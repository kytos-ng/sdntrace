"""
    Test tracing.trace_entries
"""

from unittest.mock import MagicMock, patch
import time
import pytest
from napps.amlight.sdntrace.tracing.trace_msg import TraceMsg
from napps.amlight.sdntrace.tracing.trace_manager import TraceManager
from napps.amlight.sdntrace.tracing.tracer import TracePath
from napps.amlight.sdntrace.tracing.rest import FormatRest
from napps.amlight.sdntrace.shared.switches import Switches

from kytos.lib.helpers import get_controller_mock


# pylint: disable=too-many-public-methods, too-many-lines,
# pylint: disable=protected-access, too-many-locals
class TestTracePath:
    """Test all combinations for DPID"""

    @pytest.fixture(autouse=True)
    def commomn_patches(self, request):
        """This function handles setup and cleanup for patches"""
        # This fixture sets up the common patches,
        # and a finalizer is added using addfinalizer to stop
        # the common patches after each test. This ensures that the cleanup
        # is performed after each test, and additional patch decorators
        # can be used within individual test functions.

        patcher = patch("kytos.core.helpers.run_on_thread", lambda x: x)
        mock_patch = patcher.start()

        _ = request.function.__name__

        def cleanup():
            patcher.stop()

        request.addfinalizer(cleanup)
        return mock_patch

    def setup_method(self):
        """Set up before each test method"""
        TraceManager.run_traces = MagicMock()
        self.trace_manager = TraceManager(controller=get_controller_mock())

        # This variable is used to initiate the Singleton class so
        # these tests can run on their own.
        self._auxiliar = Switches(MagicMock())

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors.aget_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    async def test_tracepath(
        self,
        mock_trace_loop,
        mock_get_switch,
        mock_aswitch_colors,
        mock_switch_colors,
    ):
        """Test tracepath initial result item. Mocking tracepath loop
        to get just one step."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"
        mock_aswitch_colors.return_value = "ee:ee:ee:ee:ee:01"

        switch = MagicMock()
        switch.dpid = "00:00:00:00:00:00:00:01"
        mock_get_switch.return_value = switch

        # Mock tracepath loop to create only the initial result item
        mock_trace_loop.return_value = True

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)
        await tracer.tracepath()

        # Retrieve trace result created from tracepath
        result = self.trace_manager.get_result(trace_id)

        assert result["request_id"] == 111
        assert len(result["result"]) == 1
        assert result["result"][0]["type"] == "starting"
        assert result["result"][0]["dpid"] == dpid["dpid"]
        assert result["result"][0]["port"] == dpid["in_port"]

        assert result["request"]["trace"]["switch"]["dpid"] == dpid["dpid"]
        assert result["request"]["trace"]["switch"]["in_port"] == dpid["in_port"]
        assert result["request"]["trace"]["eth"]["dl_vlan"] == eth["dl_vlan"]
        assert mock_switch_colors.call_count == 1
        assert mock_aswitch_colors.call_count == 1

    @patch("napps.amlight.sdntrace.shared.colors.Colors.aget_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    async def test_tracepath_result(
        self, mock_trace_loop, mock_get_switch, mock_switch_colors, mock_aswitch_colors
    ):
        """Test tracepath initial result item. Patching the tracepath loop
        to test multiple steps."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"
        mock_aswitch_colors.return_value = "ee:ee:ee:ee:ee:01"

        # Patch Switches.get_switch
        def wrap_get_switch(dpid):
            switch = MagicMock()
            switch.dpid = dpid
            return switch

        mock_get_switch.side_effect = wrap_get_switch

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)

        # Patch tracepath loop to create a second result item
        # pylint: disable=unused-argument
        def wrap_tracepath_loop(entries, color, switch):
            rest = FormatRest()
            rest.add_trace_step(
                tracer.trace_result,
                trace_type="trace",
                dpid="00:00:00:00:00:00:00:03",
                port=3,
            )
            return True

        mock_trace_loop.side_effect = wrap_tracepath_loop

        # Execute tracepath
        await tracer.tracepath()

        # Retrieve trace result created from tracepath
        result = self.trace_manager.get_result(trace_id)

        assert result["request_id"] == 111
        assert len(result["result"]) == 2
        assert result["result"][0]["type"] == "starting"
        assert result["result"][0]["dpid"] == dpid["dpid"]
        assert result["result"][0]["port"] == dpid["in_port"]

        assert result["result"][1]["type"] == "trace"
        assert result["result"][1]["dpid"] == "00:00:00:00:00:00:00:03"
        assert result["result"][1]["port"] == 3

        assert result["request"]["trace"]["switch"]["dpid"] == dpid["dpid"]
        assert result["request"]["trace"]["switch"]["in_port"] == dpid["in_port"]
        assert result["request"]["trace"]["eth"]["dl_vlan"] == eth["dl_vlan"]
        assert mock_switch_colors.call_count == 1
        assert mock_aswitch_colors.call_count == 1

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    @patch("napps.amlight.sdntrace.tracing.tracer.send_packet_out")
    async def test_send_trace_probe(
        self,
        mock_send_packet_out,
        mock_trace_loop,
        mock_get_switch,
        mock_switch_colors,
    ):
        """Test send_trace_probe send and receive."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"

        mock_send_packet_out.return_value = True

        switch_obj = MagicMock()
        switch_obj.dpid = "00:00:00:00:00:00:00:01"
        mock_get_switch.return_value = switch_obj

        # Mock tracepath loop to create only the initial result item
        mock_trace_loop.return_value = True

        # Creating a fake packet in
        msg = TraceMsg()
        msg.request_id = 111
        pkt_in = {}
        pkt_in["dpid"] = "00:00:00:00:00:00:00:01"
        pkt_in["in_port"] = 1
        pkt_in["msg"] = msg
        pkt_in["ethernet"] = "fake_ethernet_object"
        pkt_in["event"] = "fake_event_object"
        self.trace_manager.trace_pkt_in = [pkt_in]

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        eth = {"dl_vlan": 100, "dl_type": 2048}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)

        in_port = 1
        probe_pkt = MagicMock()

        result = await tracer.send_trace_probe(switch_obj, in_port, probe_pkt)

        mock_send_packet_out.assert_called_once()

        assert result[0]["dpid"] == "00:00:00:00:00:00:00:01"
        assert result[0]["port"] == 1
        assert result[1] == "fake_event_object"
        mock_switch_colors.assert_called_once()

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    @patch("napps.amlight.sdntrace.tracing.tracer.send_packet_out")
    async def test_send_trace_probe_timeout(
        self,
        mock_send_packet_out,
        mock_trace_loop,
        mock_get_switch,
        mock_aswitch_colors,
    ):
        """Test send_trace_probe with timeout."""
        mock_aswitch_colors.return_value = "ee:ee:ee:ee:ee:01"
        mock_send_packet_out.return_value = True

        switch_obj = MagicMock()
        switch_obj.dpid = "00:00:00:00:00:00:00:01"
        mock_get_switch.return_value = switch_obj

        # Mock tracepath loop to create only the initial result item
        mock_trace_loop.return_value = True

        # Creating a fake packet in
        self.trace_manager.trace_pkt_in = []

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        timeout = 1
        eth = {"dl_vlan": 100, "dl_type": 2048}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth, "timeout": timeout}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)

        in_port = 1
        probe_pkt = MagicMock()

        expected_time = timeout * 3
        start_time = time.time()
        result = await tracer.send_trace_probe(switch_obj, in_port, probe_pkt)
        actual_time = time.time() - start_time

        assert mock_send_packet_out.call_count == 3
        assert expected_time < actual_time, "Trace was too fast."

        assert result[0] == "timeout"
        assert result[1] is False
        mock_aswitch_colors.assert_called_once()

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    def test_check_loop(self, mock_get_switch, mock_switch_colors):
        """Test check_loop with loop detection."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"

        # Patch Switches.get_switch
        def wrap_get_switch(dpid):
            switch = MagicMock()
            switch.dpid = dpid
            return switch

        mock_get_switch.side_effect = wrap_get_switch

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        eth = {"dl_vlan": 100, "dl_type": 2048}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)

        # Patch tracepath loop to create a second result item
        rest = FormatRest()
        rest.add_trace_step(
            tracer.trace_result,
            trace_type="trace",
            dpid="00:00:00:00:00:00:00:01",
            port=1,
        )
        rest.add_trace_step(
            tracer.trace_result,
            trace_type="trace",
            dpid="00:00:00:00:00:00:00:02",
            port=2,
        )
        rest.add_trace_step(
            tracer.trace_result,
            trace_type="trace",
            dpid="00:00:00:00:00:00:00:03",
            port=3,
        )
        rest.add_trace_step(
            tracer.trace_result,
            trace_type="trace",
            dpid="00:00:00:00:00:00:00:01",
            port=1,
        )

        result = tracer.check_loop()
        mock_switch_colors.assert_called_once()
        assert result is True

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    def test_check_loop_false(self, mock_get_switch, mock_switch_colors):
        """Test check_loop with no loop detection."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"

        # Patch Switches.get_switch
        def wrap_get_switch(dpid):
            switch = MagicMock()
            switch.dpid = dpid
            return switch

        mock_get_switch.side_effect = wrap_get_switch

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        eth = {"dl_vlan": 100, "dl_type": 2048}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)

        # Patch tracepath loop to create a second result item
        rest = FormatRest()
        rest.add_trace_step(
            tracer.trace_result,
            trace_type="trace",
            dpid="00:00:00:00:00:00:00:01",
            port=1,
        )
        rest.add_trace_step(
            tracer.trace_result,
            trace_type="trace",
            dpid="00:00:00:00:00:00:00:02",
            port=2,
        )

        result = tracer.check_loop()
        mock_switch_colors.assert_called_once()
        assert result == 0

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    def test_check_loop_port_different(self, mock_get_switch, mock_switch_colors):
        """Test check_loop with same switch and different port."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"

        # Patch Switches.get_switch
        def wrap_get_switch(dpid):
            switch = MagicMock()
            switch.dpid = dpid
            return switch

        mock_get_switch.side_effect = wrap_get_switch

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        eth = {"dl_vlan": 100, "dl_type": 2048}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)

        # Patch tracepath loop to create a second result item
        rest = FormatRest()
        rest.add_trace_step(
            tracer.trace_result,
            trace_type="trace",
            dpid="00:00:00:00:00:00:00:01",
            port=1,
        )
        rest.add_trace_step(
            tracer.trace_result,
            trace_type="trace",
            dpid="00:00:00:00:00:00:00:02",
            port=2,
        )
        rest.add_trace_step(
            tracer.trace_result,
            trace_type="trace",
            dpid="00:00:00:00:00:00:00:01",
            port=10,
        )

        result = tracer.check_loop()
        mock_switch_colors.assert_called_once()
        assert result == 0

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    @patch("napps.amlight.sdntrace.tracing.tracer.prepare_next_packet")
    async def test_tracepath_loop(
        self,
        mock_next_packet,
        mock_probe,
        mock_get_switch,
        mock_switch_colors,
    ):
        """Test tracepath loop method. This test force the return
        after one normal trace."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"

        # Patch Switches.get_switch
        def wrap_get_switch(dpid):
            switch = MagicMock()
            switch.dpid = dpid
            return switch

        mock_get_switch.side_effect = wrap_get_switch

        mock_probe.return_value = [
            {"dpid": "00:00:00:00:00:00:00:01", "port": 1},
            "fake_event_object",
        ]

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)

        # Mock the next packt to stop the trace loop
        # pylint: disable=unused-argument
        def wrap_next_packet(entries, result, packet_in):
            tracer.trace_ended = True
            return "", "", ""

        mock_next_packet.side_effect = wrap_next_packet

        color = {"color_field": "dl_src", "color_value": "ee:ee:ee:ee:01:2c"}

        # Execute tracepath
        await tracer.tracepath_loop(trace_entries, color, switch)
        result = tracer.trace_result

        mock_probe.assert_called_once()
        mock_switch_colors.assert_called_once()
        assert result[0]["type"] == "trace"
        assert result[0]["dpid"] == "00:00:00:00:00:00:00:01"

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    async def test_tracepath_loop_timeout(
        self,
        mock_probe,
        mock_get_switch,
        mock_switch_colors,
    ):
        """Test tracepath loop method finishing with timeout."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"

        # Patch Switches.get_switch
        def wrap_get_switch(dpid):
            switch = MagicMock()
            switch.dpid = dpid
            return switch

        mock_get_switch.side_effect = wrap_get_switch

        mock_probe.return_value = ["timeout", "fake_event_object"]

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        color = {"color_field": "dl_src", "color_value": "ee:ee:ee:ee:01:2c"}

        # Execute tracepath
        tracer = TracePath(self.trace_manager, trace_id, trace_entries)
        await tracer.tracepath_loop(trace_entries, color, switch)

        result = tracer.trace_result

        mock_probe.assert_called_once()
        mock_switch_colors.assert_called_once()
        assert result[0]["type"] == "last"
        assert result[0]["reason"] == "done"
        assert result[0]["msg"] == "none"

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    @patch("napps.amlight.sdntrace.tracing.tracer.prepare_next_packet")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.check_loop")
    async def test_tracepath_loop_with_loop(
        self,
        mock_check_loop,
        mock_next_packet,
        mock_probe,
        mock_get_switch,
        mock_switch_colors,
    ):
        """Test tracepath loop method finishing with a loop."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"
        mock_check_loop.return_value = True

        # Patch Switches.get_switch
        def wrap_get_switch(dpid):
            switch = MagicMock()
            switch.dpid = dpid
            return switch

        mock_get_switch.side_effect = wrap_get_switch

        mock_probe.return_value = [
            {"dpid": "00:00:00:00:00:00:00:01", "port": 1},
            "fake_event_object",
        ]

        # Trace id to recover the result
        trace_id = 111

        # Creating trace entries
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)

        # Mock the next packt to stop the trace loop
        # pylint: disable=unused-argument
        def wrap_next_packet(entries, result, packet_in):
            tracer.trace_ended = True
            return "", "", ""

        mock_next_packet.side_effect = wrap_next_packet

        color = {"color_field": "dl_src", "color_value": "ee:ee:ee:ee:01:2c"}

        # Execute tracepath
        await tracer.tracepath_loop(trace_entries, color, switch)
        result = tracer.trace_result

        mock_check_loop.assert_called_once()
        mock_next_packet.assert_not_called()
        mock_probe.assert_called_once()
        assert mock_get_switch.call_count == 3
        mock_switch_colors.assert_called_once()

        assert result[0]["type"] == "trace"
        assert result[0]["dpid"] == "00:00:00:00:00:00:00:01"
