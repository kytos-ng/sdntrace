"""
    Trace Manager Class
"""


import dill
import time
from janus import Queue
from _thread import start_new_thread as new_thread
from collections import defaultdict
from typing import Optional

from kytos.core import log
from napps.amlight.sdntrace import settings
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.shared.colors import Colors
from napps.amlight.sdntrace.tracing.tracer import TracePath
from napps.amlight.sdntrace.tracing.trace_pkt import process_packet
from napps.amlight.sdntrace.tracing.trace_entries import TraceEntries
from napps.amlight.sdntrace.tracing.trace_msg import TraceMsg


class TraceManager(object):
    """
        The TraceManager class is the class responsible to
        manage all trace requests.
    """

    def __init__(self, controller):
        """Initialization of the TraceManager class
        Args:
             controller = Kytos.core.controller object
        """
        # Controller
        self.controller = controller

        # Trace ID used to distinguish each trace
        self._id = 30000

        # Trace queues
        self._request_dict = dict()
        self._request_queue = None
        self._results_queue = dict()
        self._running_traces:dict[int, TraceEntries] = dict()

        # Counters
        self._total_traces_requested = 0

        # PacketIn queue with Probes
        self._trace_pkt_in = defaultdict(Queue)

        self._is_tracing_running = False

        self._async_loop = None
        # To start traces
        self.run_traces()

    def stop_traces(self):
        if self._is_tracing_running:
            self._is_tracing_running = False
            self._request_queue.close()
        for trace_obj in self._running_traces.values():
            trace_obj.trace_ended = True
            if trace_obj.id in self._trace_pkt_in:
                self._trace_pkt_in[trace_obj.id].close()

    def is_tracing_running(self):
        return self._is_tracing_running

    def run_traces(self):
        """
        Create the task to search for traces _run_traces.
        """
        self._request_queue = Queue()
        self._is_tracing_running = True
        new_thread(self._run_traces, ())

    def _run_traces(self):
        """ Thread that will keep reading the self._request_dict
        queue looking for new trace requests to run.
        """
        try:
            while self.is_tracing_running():
                try:
                    if not self.limit_traces_reached():
                        request_id = self._request_queue.sync_q.get()
                        entries = self._request_dict[request_id]
                        new_thread(self._spawn_trace, (request_id, entries))
                        # After starting traces for new requests,
                        # remove them from self._request_dict
                        del self._request_dict[request_id]
                    else:
                        # Wait for traces to end
                        time.sleep(1)
                except Exception as error:  # pylint: disable=broad-except
                    log.error("Trace Error: %s" % error)
        except RuntimeError:
            log.warning("Ignored trace request while sdntrace was shutting down.")

    def _spawn_trace(self, trace_id, trace_entries):
        """ Once a request is found by the run_traces method,
        instantiate a TracePath class and run the tracepath

        Args:
            trace_id: trace request id
            trace_entries: TraceEntries class
        """
        
        log.info("Creating task to trace request id %s..." % trace_id)
        tracer = TracePath(self, trace_id, trace_entries)

        self._running_traces[trace_id] = tracer
        tracer.tracepath()

    def add_result(self, trace_id, result):
        """Used to save trace results to self._results_queue

        Args:
            trace_id: trace ID
            result: trace result generated using tracer
        """
        self._results_queue[trace_id] = result
        self._running_traces.pop(trace_id, None)

    def avoid_duplicated_request(self, entries):
        """Verify if any of the requested queries has the same entries.
        If so, ignore it

        Args:
            entries: entries provided by user via REST.
        Return:
            True: if exists a similar request
            False: otherwise
        """
        for request in self._request_dict.copy():
            if entries == self._request_dict[request]:
                return True
        return False

    @staticmethod
    async def is_entry_valid(entries):
        """ This method validates all params provided, including
        if the switch/dpid requested exists.

        Args:
            entries: dictionary with user request
        Returns:
            TraceEntries class
            Error msg
        """
        try:
            trace_entries = TraceEntries()
            trace_entries.load_entries(entries)
        except ValueError as msg:
            return str(msg)

        init_switch = Switches().get_switch(trace_entries.dpid)
        if isinstance(init_switch, bool):
            return "Unknown Switch"
        color = await Colors().aget_switch_color(init_switch.dpid)

        if len(color) == 0:
            return "Switch not Colored"

        # TODO: get Coloring API to confirm color_field

        return trace_entries

    def get_id(self):
        """ID generator for each trace. Useful in case
        of parallel requests

        Returns:
            integer to be the new request/trace id
        """
        self._id += 1
        return self._id

    def get_result(self, trace_id):
        """Used by external apps to get a trace result using the trace ID

        Returns:
            result from self._results_queue
            msg depending of the status (unknown, pending, or active)
        """
        trace_id = int(trace_id)
        try:
            return self._results_queue[trace_id]
        except (ValueError, KeyError):
            if trace_id in self._running_traces:
                return {'msg': 'trace in process'}
            elif trace_id in self._request_dict:
                return {'msg': 'trace pending'}
            return {'msg': 'unknown trace id'}

    def get_results(self):
        """Used by external apps to get all trace results. Useful
        to see all requests and results

        Returns:
            list of results
        """
        return self._results_queue

    def limit_traces_reached(self):
        """ Control the number of active traces running in parallel. Protects the
        switches and avoid DoS.

        Returns:
            True: if the number of traces running is equal/more
                than settings.PARALLEL_TRACES
            False: if it is not.
        """
        if len(self._running_traces) >= settings.PARALLEL_TRACES:
            return True
        return False

    async def new_trace(self, trace_entries):
        """Receives external requests for traces.

        Args:
            trace_entries: TraceEntries Class
        Returns:
            int with the request/trace id
        """

        trace_id = self.get_id()

        # Add to request_queue
        self._request_dict[trace_id] = trace_entries
        try:
            await self._request_queue.async_q.put(trace_id)
        except RuntimeError:
            pass

        # Statistics
        self._total_traces_requested += 1

        return trace_id

    def number_pending_requests(self):
        """Used to check if there are entries to be traced

        Returns:
            length of self._request_dict
        """
        return len(self._request_dict)

    def get_unpickled_packet_eth(self, ethernet) -> Optional[TraceMsg]:
        """Unpickle PACKET_IN ethernet or catch errors."""
        try:
            msg = dill.loads(process_packet(ethernet))
        except dill.UnpicklingError as err:
            log.error(f"Error getting msg from PacketIn: {err}")
            return None
        return msg

    async def queue_probe_packet(self, event, ethernet, in_port, switch):
        """Used by sdntrace.packet_in_handler. Only tracing probes
        get to this point. Adds the PacketIn msg received to the
        trace_pkt_in queue.

        Args:
            event: PacketIn msg
            ethernet: ethernet frame
            in_port: in_port
            switch: kytos.core.switch.Switch() class
        """
        msg = self.get_unpickled_packet_eth(ethernet)
        if msg is None:
            return
        pkt_in = dict()
        pkt_in["dpid"] = switch.dpid
        pkt_in["in_port"] = in_port
        pkt_in["msg"] = msg
        pkt_in["ethernet"] = ethernet
        pkt_in["event"] = event
        request_id = pkt_in['msg'].request_id

        if request_id not in self._results_queue:
            # This queue stores all PacketIn message received
            try:
                await self._trace_pkt_in[request_id].async_q.put(pkt_in)
            except RuntimeError:
                # If queue was close do nothing
                pass

    # REST calls

    async def rest_new_trace(self, entries: dict):
        """Used for the REST PUT call

        Args:
            entries: user provided parameters to trace
        Returns:
            Trace_ID in JSON format
            Error msg if entries has invalid data
        """
        result = dict()
        trace_entries = await self.is_entry_valid(entries)
        if not isinstance(trace_entries, TraceEntries):
            result['result'] = {'error': trace_entries}
            return result

        if self.avoid_duplicated_request(entries):
            result['result'] = {'error': "Duplicated Trace Request ignored"}
            return result

        trace_id = await self.new_trace(trace_entries)
        result['result'] = {'trace_id': trace_id}
        return result

    def rest_get_result(self, trace_id):
        """Used for the REST GET call

        Returns:
            get_result in JSON format
        """
        return self.get_result(trace_id)

    def rest_list_results(self):
        """Used for the REST GET call

        Returns:
            get_results in JSON format
        """
        return self.get_results()

    def rest_list_stats(self):
        """ Used to export some info about the TraceManager.
        Total number of requests, number of active traces, number of
        pending traces, list of traces pending
        Returns:
                Total number of requests
                number of active traces
                number of pending traces
                list of traces pending
        """
        stats = dict()
        stats['number_of_requests'] = self._total_traces_requested
        stats['number_of_running_traces'] = len(self._running_traces)
        stats['number_of_pending_traces'] = len(self._request_dict)
        stats['list_of_pending_traces'] = self._results_queue

        return stats
