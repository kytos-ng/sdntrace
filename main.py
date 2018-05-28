"""Main module of amlight/sdntrace Kytos Network Application.

An OpenFlow Data Path Trace.

The AmLight SDNTrace is a Kytos Network Application allows users to trace a
path directly from the data plane. Originally written for Ryu
(github.com/amlight/sdntrace).

Steps:
    1 - User requests a trace using a specific flow characteristic,
        for example VLAN = 1000 and Dest IP address = 2.2.2.2
    2 - REST module inserts trace request in a queue provided by the
        TraceManager
    3 - The TraceManager runs the Tracer, basically sending PacketOuts
        and waiting for PacketIn until reaching a timeout
    4 - After Timeout, result is provided back to REST that provides it
        back to user
Dependencies:
    * - amlight/coloring Napp will color all switches

At this moment, OpenFlow 1.0 and 1.3 are supported.
"""


from flask import jsonify, request
from kytos.core import KytosNApp, log, rest
from kytos.core.helpers import listen_to
from napps.amlight.sdntrace import settings
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.tracing.trace_manager import TraceManager
from napps.amlight.sdntrace.backends.of_parser import process_packet_in


VERSION = '0.3'


class Main(KytosNApp):
    """Main class of amlight/sdntrace NApp.

    REST methods:
        /sdntrace/trace ['PUT'] - request a trace
        /sdntrace/trace ['GET'] - list of previous trace requests and results
        /sdntrace/trace/<trace_id> - get the results of trace requested
        /sdntrace/stats - Show the number of requests received and active
        /sdntrace/settings - list the settings
    """

    def setup(self):
        """ Default Kytos/Napps setup call. """
        log.info("Starting Kytos SDNTrace App version %s!" % VERSION)

        # Create list of switches
        self.switches = Switches(self.controller.switches)  # noqa: E501  pylint: disable=attribute-defined-outside-init

        # Instantiate TraceManager
        self.tracing = TraceManager(self.controller)  # pylint: disable=W0201

    @listen_to('kytos/of_core.v0x0[14].messages.in.ofpt_packet_in')
    def handle_packet_in(self, event):
        """ Receives OpenFlow PacketIn msgs and search from trace packets.
        If process_packet_in returns 0,0,0, it means it is not a probe
        packet. Otherwise, store the msg for later use by Tracers.

        Args:
            event (KycoPacketIn): Received Event
        """
        ethernet, in_port, switch = process_packet_in(event)
        if not isinstance(ethernet, int):
            self.tracing.queue_probe_packet(event, ethernet,
                                            in_port, switch)

    def execute(self):
        """ Kytos Napp execute method """
        pass

    def shutdown(self):
        """ Kytos Napp shutdown method"""
        pass

    @rest('/trace', methods=['PUT'])
    def run_trace(self):
        """ Submit a trace request

        Return:
            trace ID in JSON format
        """
        return jsonify(self.tracing.rest_new_trace(request.get_json()))

    @rest('/trace', methods=['GET'])
    def get_results(self):
        """ List all traces performed so far.

        Return:
            rest_list_results in JSON format
        """
        return jsonify(self.tracing.rest_list_results())

    @rest('/trace/<trace_id>', methods=['GET'])
    def get_result(self, trace_id):
        """ List All Traces performed since the Napp loaded

        Return:
            rest_get_result in JSON format
        """
        return jsonify(self.tracing.rest_get_result(trace_id))

    @rest('/stats', methods=['GET'])
    def get_stats(self):
        """ Get statistics

        Return:
            rest_list_stats in JSON format
        """
        return jsonify(self.tracing.rest_list_stats())

    @staticmethod
    @rest('/settings', methods=['GET'])
    def list_settings():
        """ List the SDNTrace settings

        Return:
            SETTINGS in JSON format
        """
        settings_dict = dict()
        settings_dict['color_field'] = settings.COLOR_FIELD
        settings_dict['color_value'] = settings.COLOR_VALUE
        settings_dict['trace_interval'] = settings.TRACE_INTERVAL
        settings_dict['parallel_traces'] = settings.PARALLEL_TRACES
        settings_dict['sdntrace_version'] = VERSION
        return jsonify(settings_dict)
