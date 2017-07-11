"""
    Tracer main class
"""
import time
import copy
from kytos.core import log
from napps.amlight.sdntrace.tracing.trace_pkt import generate_trace_pkt, prepare_next_packet
from napps.amlight.sdntrace.tracing.rest import FormatRest
from napps.amlight.sdntrace.tracing.packet_out import send_packet_out
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.shared.colors import Colors
from napps.amlight.sdntrace import settings


class TracePath(object):
    """
        Tracer main class - responsible for running traces.
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
            trace_manager: main TraceManager class - needed because Kytos.controller
            r_id: request ID
            initial_entries: user entries for trace
        """
        self.switches = Switches()
        self.trace_mgr = trace_manager
        self.id = r_id
        self.init_entries = initial_entries

        self.trace_result = []
        self.trace_ended = False
        self.init_switch = self.get_init_switch()
        self.rest = FormatRest()
        self.mydomain = settings.MY_DOMAIN

    def get_init_switch(self):
        """Get the Switch class of the switch requested by user

        Returns:
            Switch class
        """
        dpid = self.init_entries['trace']['switch']['dpid']
        return Switches().get_switch(dpid)

    def tracepath(self):
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
        log.warning("Starting Trace Path for ID %s" % self.id)

        entries = copy.deepcopy(self.init_entries)
        color = Colors().get_switch_color(self.init_switch.dpid)
        switch = self.init_switch
        # Add initial trace step
        self.rest.add_trace_step(self.trace_result, trace_type='starting',
                                 dpid=switch.dpid,
                                 port=entries['trace']['switch']['in_port'])

        # A loop waiting for 'trace_ended'. It changes to True when reaches timeout
        while not self.trace_ended:
            in_port, probe_pkt = generate_trace_pkt(entries, color, self.id,
                                                    self.mydomain)
            result, packet_in = self.send_trace_probe(switch, in_port, probe_pkt)
            if result == 'timeout':
                self.rest.add_trace_step(self.trace_result, trace_type='last')
                log.warning("Intra-Domain Trace Completed!")
                self.trace_ended = True
            else:
                self.rest.add_trace_step(self.trace_result, trace_type='trace',
                                         dpid=result['dpid'], port=result['port'])
                if self.check_loop():
                    self.rest.add_trace_step(self.trace_result, trace_type='last',
                                             reason='loop')
                    self.trace_ended = True
                    break
                # If we got here, that means we need to keep going.
                entries, color, switch = prepare_next_packet(entries, result,
                                                             packet_in)

        # Add final result to trace_results_queue
        t_result = {"request_id": self.id, "result": self.trace_result,
                    "start_time": str(self.rest.start_time),
                    "total_time": self.rest.get_time(),
                    "request": self.init_entries}

        self.trace_mgr.add_result(self.id, t_result)

    def send_trace_probe(self, switch, in_port, probe_pkt):
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

        log.warning('Tracer: Sending POut to switch: %s and in_port %s '
                    % (switch.dpid, in_port))
        # send_packet_out(self.trace_mgr.controller, switch, in_port, probe_pkt.data)
        send_packet_out(self.trace_mgr.controller, switch, in_port, probe_pkt)

        while True:
            time.sleep(0.5)  # Wait 0.5 second before querying for PacketIns
            timeout_control += 1

            if timeout_control >= 3:
                return 'timeout', False

            # Check if there is any Probe PacketIn in the queue
            for pIn in self.trace_mgr.trace_pktIn:
                # Let's look for traces with our self.id
                # Each entry has the following format:
                # (pktIn_dpid, pktIn_port, TraceMsg, pkt, ev)
                # packetIn_data_request_id is the request id
                # of the packetIn.data.

                msg = pIn[2]
                if self.id == msg.request_id:
                    self.clear_trace_pkt_in()
                    return {'dpid': pIn[0], "port": pIn[1]}, pIn[4]
                else:
                    log.warning('Sending PacketOut Again')
                    # send_packet_out(self.trace_mgr.controller, switch, in_port, probe_pkt.data)
                    send_packet_out(self.trace_mgr.controller, switch, in_port, probe_pkt)

    def clear_trace_pkt_in(self):
        """ Once the probe PacketIn was processed, delete it from queue """
        for pIn in self.trace_mgr.trace_pktIn:
            msg = pIn[2]
            if self.id == msg.request_id:
                self.trace_mgr.trace_pktIn.remove(pIn)

    def check_loop(self):
        """ Check if there are equal entries """
        i = 0
        last = len(self.trace_result) - 1
        while i < last:
            if self.trace_result[i]['dpid'] == self.trace_result[last]['dpid']:
                if self.trace_result[i]['port'] == self.trace_result[last]['port']:
                    return True
            i += 1
        return 0
