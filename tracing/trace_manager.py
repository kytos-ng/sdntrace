"""
    Trace Manager Class
"""


import time
import dill
import asyncio
from _thread import start_new_thread as new_thread

from kytos.core import log
from napps.amlight.sdntrace import settings
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.shared.colors import Colors
from napps.amlight.sdntrace.tracing.tracer import TracePath
from napps.amlight.sdntrace.tracing.trace_pkt import process_packet
from napps.amlight.sdntrace.tracing.trace_entries import TraceEntries


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
        self._request_queue = dict()
        self._results_queue = dict()
        self._running_traces = dict()

        # Counters
        self._total_traces_requested = 0

        # PacketIn queue with Probes
        self.trace_pkt_in = []

        self._is_tracing_running = True

        self.tasks: list[asyncio.Task] = []
        self._async_loop = None
        # To start traces
        self.run_traces(settings.TRACE_INTERVAL)        

    def stop_traces(self):
        self._is_tracing_running = False
        for task in self.tasks:
            task.cancel()

    def is_tracing_running(self):
        return self._is_tracing_running
    
    def run_traces(self, trace_interval):
        """
        Create the task to search for traces _run_traces.
        """
        self._async_loop = asyncio.get_running_loop()
        task = self._async_loop.create_task(
            self._run_traces(trace_interval)
        )
        self.tasks.append(task)

    async def _run_traces(self, trace_interval):
        """ Thread that will keep reading the self._request_queue
        queue looking for new trace requests to run.

        Args:
            trace_interval = sleeping time
        """
        while self.is_tracing_running():
            if self.number_pending_requests() > 0:
                try:
                    new_request_ids = []
                    for req_id in self._request_queue.copy():
                        if not self.limit_traces_reached():
                            entries = self._request_queue[req_id]
                            self._running_traces[req_id] = entries
                            task = self._async_loop.create_task(
                                self._spawn_trace(req_id, entries)
                            )
                            self.tasks.append(task)
                            new_request_ids.append(req_id)
                        else:
                            break
                    # After starting traces for new requests,
                    # remove them from self._request_queue
                    for rid in new_request_ids:
                        del self._request_queue[rid]
                except Exception as error:  # pylint: disable=broad-except
                    log.error("Trace Error: %s" % error)
            await asyncio.sleep(trace_interval)

    async def _spawn_trace(self, trace_id, trace_entries):
        """ Once a request is found by the run_traces method,
        instantiate a TracePath class and run the tracepath

        Args:
            trace_id: trace request id
            trace_entries: TraceEntries class
        """
        
        log.info("Creating task to trace request id %s..." % trace_id)
        tracer = TracePath(self, trace_id, trace_entries)
        await tracer.tracepath()

        del self._running_traces[trace_id]

    def add_result(self, trace_id, result):
        """Used to save trace results to self._results_queue

        Args:
            trace_id: trace ID
            result: trace result generated using tracer
        """
        self._results_queue[trace_id] = result

    def avoid_duplicated_request(self, entries):
        """Verify if any of the requested queries has the same entries.
        If so, ignore it

        Args:
            entries: entries provided by user via REST.
        Return:
            True: if exists a similar request
            False: otherwise
        """
        for request in self._request_queue.copy():
            if entries == self._request_queue[request]:
                return True
        return False

    @staticmethod
    def is_entry_valid(entries):
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
        color = Colors().get_switch_color(init_switch.dpid)

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
            elif trace_id in self._request_queue:
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

    def new_trace(self, trace_entries):
        """Receives external requests for traces.

        Args:
            trace_entries: TraceEntries Class
        Returns:
            int with the request/trace id
        """

        trace_id = self.get_id()

        # Add to request_queue
        self._request_queue[trace_id] = trace_entries

        # Statistics
        self._total_traces_requested += 1

        return trace_id

    def number_pending_requests(self):
        """Used to check if there are entries to be traced

        Returns:
            length of self._request_queue
        """
        return len(self._request_queue)

    def queue_probe_packet(self, event, ethernet, in_port, switch):
        """Used by sdntrace.packet_in_handler. Only tracing probes
        get to this point. Adds the PacketIn msg received to the
        trace_pkt_in queue.

        Args:
            event: PacketIn msg
            ethernet: ethernet frame
            in_port: in_port
            switch: kytos.core.switch.Switch() class
        """
        pkt_in = dict()

        pkt_in["dpid"] = switch.dpid
        pkt_in["in_port"] = in_port
        pkt_in["msg"] = dill.loads(process_packet(ethernet))
        pkt_in["ethernet"] = ethernet
        pkt_in["event"] = event

        # This queue stores all PacketIn message received
        self.trace_pkt_in.append(pkt_in)

    # REST calls

    def rest_new_trace(self, entries):
        """Used for the REST PUT call

        Args:
            entries: user provided parameters to trace
        Returns:
            Trace_ID in JSON format
            Error msg if entries has invalid data
        """
        result = dict()
        trace_entries = self.is_entry_valid(entries)
        if not isinstance(trace_entries, TraceEntries):
            result['result'] = {'error': trace_entries}
            return result

        if self.avoid_duplicated_request(entries):
            result['result'] = {'error': "Duplicated Trace Request ignored"}
            return result

        trace_id = self.new_trace(trace_entries)
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
        stats['number_of_pending_traces'] = len(self._request_queue)
        stats['list_of_pending_traces'] = self._results_queue

        return stats
