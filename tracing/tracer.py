"""
    Tracer main class
"""
import time
import asyncio
import copy
from kytos.core import log
from napps.amlight.sdntrace.tracing.trace_pkt import generate_trace_pkt
from napps.amlight.sdntrace.tracing.trace_pkt import prepare_next_packet
from napps.amlight.sdntrace.tracing.rest import FormatRest
from napps.amlight.sdntrace.backends.of_parser import send_packet_out
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.shared.colors import Colors


class TracePath(object):
    """ Tracer main class - responsible for running traces.
    It is composed of two parts:
     1) Sending PacketOut messages to switches
     2) Reading the pktIn queue with PacketIn received

    There are a few possibilities of result (except for errors):
    - Timeouts ({'trace': 'completed'}) - even positive results end w/
        timeouts.
    - Loops ({'trace': 'loop'}) - every time an entry is seen twice
        in the trace_result queue, we stop

    Some things to take into consideration:
    - we can have parallel traces
    - we can have flow rewrite along the path (vlan translation, f.i)
    """

    def __init__(self, trace_manager, r_id, initial_entries):
        """
        Args:
            trace_manager: main TraceManager class - needed for
            Kytos.controller
            r_id: request ID
            initial_entries: user entries for trace
        """
        self.switches = Switches()
        self.trace_mgr = trace_manager
        self.id = r_id
        self.init_entries = initial_entries

        self.trace_task = None
        self.step = 0
        self.queue_packet_in = asyncio.Queue()
        self.trace_result = []
        self.trace_ended = False
        self.init_switch = self.get_init_switch()
        self.loop = asyncio.get_event_loop()
        self.rest = FormatRest()

    def get_init_switch(self):
        """Get the Switch class of the switch requested by user

        Returns:
            Switch class
        """
        return Switches().get_switch(self.init_entries.dpid)

    async def tracepath(self):
        """
            Do the trace path
            The logic is very simple:
            1 - Generate the probe packet using entries provided
            2 - Results a result and the packet_in (used to generate new probe)
                Possible results: 'timeout' meaning the end of trace
                                  or the trace step {'dpid', 'port'}
                Some networks do vlan rewriting, so it is important to get the
                packetIn msg with the header
            3 - If result is a trace step, send PacketOut to the switch that
                originated the PacketIn. Repeat till reaching timeout
        """
        log.warning("Starting Trace Path ID: %s" % self.id)
        try:
            entries = copy.deepcopy(self.init_entries)
            color = await Colors().aget_switch_color(self.init_switch.dpid)
            switch = self.init_switch
            # Add initial trace step
            self.rest.add_trace_step(self.trace_result, trace_type='starting',
                                     dpid=switch.dpid,
                                     port=entries.in_port)

            # A loop waiting for 'trace_ended'.
            # It changes to True when reaches timeout
            await self.tracepath_loop(entries, color, switch)
            # Add final result to trace_results_queue
            t_result = {"request_id": self.id,
                        "result": self.trace_result,
                        "start_time": str(self.rest.start_time),
                        "total_time": self.rest.get_time(),
                        "request": self.init_entries.init_entries}

            self.trace_mgr.add_result(self.id, t_result)
            self.clear_trace_pkt_in()
        except asyncio.CancelledError:
            log.warning(f"Trace {self.id} is getting cancelled.")

    async def tracepath_loop(self, entries, color, switch):
        """ This method sends the packet_out per hop, create the result
        to be posted via REST.
        """
        # A loop waiting for 'trace_ended'.
        # It changes to True when reaches timeout
        while not self.trace_ended:
            in_port, probe_pkt = generate_trace_pkt(entries, color, self.id, self.step)
            result, packet_in = await self.send_trace_probe(switch, in_port,
                                                            probe_pkt)
            self.step += 1
            if result == 'timeout':
                self.rest.add_trace_step(self.trace_result, trace_type='last')
                log.warning("Trace %s: Trace Completed!" % self.id)
                self.trace_ended = True
            else:
                self.rest.add_trace_step(self.trace_result,
                                         trace_type='trace',
                                         dpid=result['dpid'],
                                         port=result['port'])
                if self.check_loop():
                    self.rest.add_trace_step(self.trace_result,
                                             trace_type='last',
                                             reason='loop')
                    self.trace_ended = True
                    break
                # If we got here, that means we need to keep going.
                entries, color, switch = await prepare_next_packet(entries, result,
                                                                    packet_in)

    async def send_trace_probe(self, switch, in_port, probe_pkt):
        """ This method sends the PacketOut and checks if the
        PacketIn was received in 3 seconds.

        Args:
            switch: target switch to start with
            in_port: target port to start with
            probe_pkt: ethernet frame to send (PacketOut.data)

        Returns:
            Timeout
            {switch & port}
        """
        timeout_control = 0  # Controls the timeout of 1 second and two tries
        while not self.trace_ended:
            log.warning(f'Trace {self.id}: Sending POut to switch:'
                        f' {switch.dpid} and in_port {in_port}.'
                        f' Timeout: {self.init_entries.timeout}')
            await send_packet_out(self.trace_mgr.controller,
                                   switch, in_port, probe_pkt)

            try:
                pkt_in_msg = await asyncio.wait_for(
                    self.get_packet_in(), timeout=self.init_entries.timeout
                )
            except asyncio.TimeoutError:
                pkt_in_msg = None

            if pkt_in_msg:
                result = {"dpid": pkt_in_msg["dpid"],
                          "port": pkt_in_msg["in_port"]}
                return result, pkt_in_msg["event"]

            timeout_control += 1
            if timeout_control >= 3:
                return 'timeout', False

    async def get_packet_in(self):
        """Wait for a PacketIn and verify if it is from the correct step."""
        while not self.trace_ended:
            pkt_in_msg = await self.trace_mgr._trace_pkt_in[self.id].get()
            msg = pkt_in_msg["msg"]
            if msg.step == self.step:
                return pkt_in_msg

    def clear_trace_pkt_in(self):
        """ Once the probe PacketIn was processed, delete it from queue."""

        # TODO: Use asyncio.Queue.shutdown() also. Python 3.13
        # self.trace_mgr._trace_pkt_in[self.id].shutdown(immediate=True)
        del self.trace_mgr._trace_pkt_in[self.id]

    def check_loop(self):
        """ Check if there are equal entries

        Return:
            True if loop
            0 if not
        """
        last = self.trace_result[-1]
        for result in self.trace_result[:-1]:
            if result['dpid'] == last['dpid']:
                if result['port'] == last['port']:
                    log.warning('Trace %s: Loop Detected on %s port %s!!' %
                                (self.id, last['dpid'], last['port']))
                    return True
        return 0
