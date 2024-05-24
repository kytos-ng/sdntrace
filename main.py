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

At this moment, OpenFlow 1.3 is supported.
"""

import pathlib

from napps.amlight.sdntrace import settings
from napps.amlight.sdntrace.backends.of_parser import process_packet_in
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.tracing.trace_manager import TraceManager

from kytos.core import KytosNApp, rest
from kytos.core.helpers import listen_to, load_spec, validate_openapi
from kytos.core.rest_api import JSONResponse, Request, get_json_or_400


class Main(KytosNApp):
    """Main class of amlight/sdntrace NApp.

    REST methods:
        /sdntrace/trace ['PUT'] - request a trace
        /sdntrace/trace ['GET'] - list of previous trace requests and results
        /sdntrace/trace/<trace_id> - get the results of trace requested
        /sdntrace/stats - Show the number of requests received and active
        /sdntrace/settings - list the settings
    """

    spec = load_spec(pathlib.Path(__file__).parent / "openapi.yml")

    def setup(self):
        """Default Kytos/Napps setup call."""

        # Create list of switches
        self.switches = Switches(
            self.controller.switches
        )  # noqa: E501  pylint: disable=attribute-defined-outside-init

        # Instantiate TraceManager
        self.tracing = TraceManager(self.controller)  # pylint: disable=W0201

    def execute(self):
        """Kytos Napp execute method"""

    def shutdown(self):
        """Execute when your napp is unloaded.

        If you have some cleanup procedure, insert it here.
        """
        self.tracing.stop_traces()

    @listen_to("kytos/of_core.v0x04.messages.in.ofpt_packet_in")
    def handle_packet_in(self, event):
        """Receives OpenFlow PacketIn msgs and search from trace packets.
        If process_packet_in returns 0,0,0, it means it is not a probe
        packet. Otherwise, store the msg for later use by Tracers.

        Args:
            event (KycoPacketIn): Received Event
        """
        ethernet, in_port, switch = process_packet_in(event)
        if not isinstance(ethernet, int):
            self.tracing.queue_probe_packet(event, ethernet, in_port, switch)

    @rest("/trace", methods=["PUT"])
    @validate_openapi(spec)
    def run_trace(self, request: Request) -> JSONResponse:
        """Submit a trace request."""
        body = get_json_or_400(request, self.controller.loop)
        return JSONResponse(self.tracing.rest_new_trace(body))

    @rest("/trace", methods=["GET"])
    def get_results(self, _request: Request) -> JSONResponse:
        """List all traces performed so far."""
        return JSONResponse(self.tracing.rest_list_results())

    @rest("/trace/{trace_id}", methods=["GET"])
    def get_result(self, request: Request) -> JSONResponse:
        """List All Traces performed since the Napp loaded."""
        trace_id = request.path_params["trace_id"]
        return JSONResponse(self.tracing.rest_get_result(trace_id))

    @rest("/stats", methods=["GET"])
    def get_stats(self, _request: Request) -> JSONResponse:
        """Get statistics."""
        return JSONResponse(self.tracing.rest_list_stats())

    @staticmethod
    @rest("/settings", methods=["GET"])
    def list_settings(_request: Request) -> JSONResponse:
        """List the SDNTrace settings

        Return:
            SETTINGS in JSON format
        """
        settings_dict = {}
        settings_dict["color_field"] = settings.COLOR_FIELD
        settings_dict["color_value"] = settings.COLOR_VALUE
        settings_dict["trace_interval"] = settings.TRACE_INTERVAL
        settings_dict["parallel_traces"] = settings.PARALLEL_TRACES
        return JSONResponse(settings_dict)
