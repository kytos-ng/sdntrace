"""
    Trace Manager Class
"""


import time
import dill
from _thread import start_new_thread as new_thread

from kytos.core import log
from napps.amlight.sdntrace import settings
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.shared.colors import Colors
from napps.amlight.sdntrace.tracing.tracer import TracePath
from napps.amlight.sdntrace.tracing.trace_pkt import process_packet


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

        # Configs
        self._my_domain = settings.MY_DOMAIN

        # Trace ID used to distinguish each trace
        self._id = 30000

        # Trace queues
        self._request_queue = dict()
        self._active_traces = dict()  # For inter-domain. Future use.
        self._results_queue = dict()
        self._running_traces = dict()

        # Statistics
        self._total_traces_requested = 0

        # PacketIn queue
        self.trace_pkt_in = []

        # Thread to start traces
        new_thread(self._run_traces, (settings.TRACE_INTERVAL,))

    def _run_traces(self, trace_interval):
        """ Kytos Thread that will keep reading the
        self.request_queue queue looking for new trace requests to run.

        Args:
            trace_interval = sleeping time
        """
        while True:
            if self.number_pending_requests() > 0:
                try:
                    request_ids = []
                    for req_id in self._request_queue:
                        if not self.limit_traces_reached():
                            entries = self._request_queue[req_id]
                            self._running_traces[req_id] = entries
                            new_thread(self._spawn_trace, (req_id, entries,))
                            request_ids.append(req_id)
                        else:
                            break
                    # After starting traces for new requests,
                    # remove them from self._request_queue
                    for rid in request_ids:
                        del self._request_queue[rid]
                except Exception as error:
                    log.error("Trace Error: %s" % error)
            time.sleep(trace_interval)

    def _spawn_trace(self, trace_id, entries):
        """Once a request is found by the run_traces method,
        instantiate a TracePath class and runs the tracepath

        Args:
            trace_id: trace request id
            entries: user entries request
        """
        log.info("Creating thread to trace request id %s..." % trace_id)
        tracer = TracePath(self, trace_id, entries)
        tracer.tracepath()
        del self._running_traces[trace_id]

    def add_result(self, trace_id, result):
        """Used to save trace results to self._results_queue

        Args:
            trace_id: trace ID
            result: trace result generated using tracer
        """
        self._results_queue[trace_id] = result

    def add_to_active_traces(self, trace_id, entries):
        """All requested traces are checked first to see if they
        are an intra or an inter domain trace. Then
        self._active_trace is populated with the following
        content
                {'trace_id':{
                    'type': ['intra'|'inter'],
                    'remote_id': if inter, int(remote trace id) or 0,
                    'service': if inter, the remote service URL or 0,
                    'status': 'running'|'complete'|'timeout'
                    }
                }

        Args:
            trace_id: trace ID
            entries: user parameters
        """
        active = dict()
        active[trace_id] = {}
        trace_type = 'intra'
        active[trace_id] = {'type': trace_type,
                            'remote_id': 0,
                            'service': 0,
                            'status': 'running',
                            'timestamp': 0}
        self._active_traces[trace_id] = active[trace_id]

        # Add to request_queue
        self._request_queue[trace_id] = entries

        # Statistics
        self._total_traces_requested += 1

    @staticmethod
    def is_entry_valid(entries):
        """ Make sure the switch selected by the user exists and
        that it has a color using the Coloring Napp.
        In fact, this method has to validate all params provided.

        Args:
            entries: dictionary with user request
        Returns:
            True: all set
            False: switch requested doesn't exist
        """
        dpid = entries['trace']['switch']['dpid']
        init_switch = Switches().get_switch(dpid)
        if isinstance(init_switch, bool):
            return False
        color = Colors().get_switch_color(init_switch.dpid)
        if len(color) is 0:
            return False
        return True

    def get_id(self):
        """ID generator for each trace. Useful in case
        of parallel requests

        Returns:
            integer to be the new request/trace id
        """
        self._id += 1
        return self._id

    def get_result(self, trace_id):
        """Used by external apps to get a trace result
        using the trace ID

        Returns:
            result from self._results_queue
            0 if trace_id not found
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
        switches and avoid DoS

        :return:
            True: if the number of traces running is equal/more
                than settings.PARALLEL_TRACES
            False: if it is not.
        """
        if len(self._running_traces) >= settings.PARALLEL_TRACES:
            return True
        return False

    def new_trace(self, entries):
        """Receives external requests for traces.

        Args:
            entries: user's options for trace
        Returns:
            int with the request/trace id
        """
        if not self.is_entry_valid(entries):
            log.warning('Request with Invalid Switch Provided')
            return 0

        if self.verify_active_new_request(entries):
            log.warning('Ignoring Duplicated Trace Request Received')
            return 0

        trace_id = self.get_id()
        # Add to active_trace and _request_queue:
        self.add_to_active_traces(trace_id, entries)
        return trace_id

    def number_pending_requests(self):
        """Used to check if there are entries to be traced

        Returns:
            lenght of self._request_queue
        """
        return len(self._request_queue)

    def process_probe_packet(self, event, ethernet, in_port, switch):
        """Used by sdntrace.packet_in_handler

        Args:
            ev: msg
            ethernet: ethernet frame
            in_port: in_port
            switch: kytos.core.switch.Switch() class
        Returns:
            False in case it is not a probe packet
            or
            tuple (pktIn_dpid, pktIn_port, pkt[4], pkt, event)
        """
        pkt_in_dpid = switch.dpid
        pkt_in_port = in_port

        msg = dill.loads(process_packet(ethernet))
        if msg.is_intra() and msg.local_domain == self._my_domain:
            # This queue stores all PacketIn message received
            pkt_in = {"dpid": pkt_in_dpid, "in_port": pkt_in_port,
                      "msg": msg, "ethernet": ethernet, "event": event}
            self.trace_pkt_in.append(pkt_in)

    def verify_active_new_request(self, entries):
        """Verify if any of the active queries has the
        same entries. If so, ignore it

        Return:
            True: if exists a similar request
            False: otherwise
        """
        for request in self._request_queue:
            if entries == self._request_queue[request]:
                return True
        return False

    # REST calls

    def rest_new_trace(self, entries):
        """Used for the REST PUT call

        Args:
            entries: user provided parameters to trace
        Returns:
            Trace_ID in JSON format
        """
        result = dict()
        t_id = self.new_trace(entries)
        if t_id is not 0:
            result['result'] = {'trace_id': t_id}
        else:
            result['result'] = {'Error': 'Invalid Switch',
                                'Entries': entries}
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
        # stats['number_of_inter_domain_traces'] = len(self._active_traces)
        stats['number_of_pending_traces'] = len(self._request_queue)
        stats['list_of_pending_traces'] = self._results_queue

        return stats
