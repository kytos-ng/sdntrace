"""
    Test tracing.trace_entries
"""
from unittest import TestCase
from unittest.mock import MagicMock, patch

from napps.amlight.sdntrace.tracing.trace_msg import TraceMsg
from napps.amlight.sdntrace.tracing.trace_manager import TraceManager
from napps.amlight.sdntrace.tracing.tracer import TracePath
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.tracing.rest import FormatRest

from kytos.lib.helpers import (
    get_interface_mock,
    get_link_mock,
    get_switch_mock,
    get_controller_mock,
)


# pylint: disable=too-many-public-methods, too-many-lines,
# pylint: disable=protected-access, too-many-locals
class TestTracePath(TestCase):
    """Test all combinations for DPID"""

    def setUp(self):
        self.create_basic_switches(get_controller_mock())

        # The decorator run_on_thread is patched, so methods that listen
        # for events do not run on threads while tested.
        # Decorators have to be patched before the methods that are
        # decorated with them are imported.
        patch("kytos.core.helpers.run_on_thread", lambda x: x).start()

        self.addCleanup(patch.stopall)
        self.trace_manager = TraceManager(controller=get_controller_mock())

    @classmethod
    def create_basic_switches(cls, controller):
        """Create basic mock switches for Kytos controller."""
        dpid_a = "00:00:00:00:00:00:00:01"
        dpid_b = "00:00:00:00:00:00:00:02"

        mock_switch_a = get_switch_mock(dpid_a, 0x04)
        mock_switch_b = get_switch_mock(dpid_b, 0x04)
        mock_interface_a = get_interface_mock("s1-eth1", 1, mock_switch_a)
        mock_interface_b = get_interface_mock("s2-eth1", 1, mock_switch_b)

        mock_link = get_link_mock(mock_interface_a, mock_interface_b)
        mock_link.id = "cf0f4071be4"
        mock_switch_a.id = dpid_a
        mock_switch_a.as_dict.return_value = {"metadata": {}}
        mock_switch_b.id = dpid_b
        mock_switch_b.as_dict.return_value = {"metadata": {}}

        controller.switches = {dpid_a: mock_switch_a, dpid_b: mock_switch_b}

        Switches(controller.switches)

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    def test_tracepath(
        self, mock_trace_loop, mock_get_switch, mock_color, mock_switch_colors
    ):
        """Test tracepath initial result item. Mocking tracepath loop
        to get just one step."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"

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
        tracer.tracepath()

        # Retrieve trace result created from tracepath
        result = self.trace_manager.get_result(trace_id)

        self.assertEqual(result["request_id"], 111)
        self.assertEqual(len(result["result"]), 1)
        self.assertEqual(result["result"][0]["type"], "starting")
        self.assertEqual(result["result"][0]["dpid"], dpid["dpid"])
        self.assertEqual(result["result"][0]["port"], dpid["in_port"])

        self.assertEqual(
            result["request"]["trace"]["switch"]["dpid"], dpid["dpid"]
        )
        self.assertEqual(
            result["request"]["trace"]["switch"]["in_port"], dpid["in_port"]
        )
        self.assertEqual(
            result["request"]["trace"]["eth"]["dl_vlan"], eth["dl_vlan"]
        )
        self.assertEqual(mock_color.call_count, 2)
        self.assertEqual(mock_switch_colors.call_count, 2)

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    def test_tracepath_result(
        self, mock_trace_loop, mock_get_switch, mock_color, mock_switch_colors
    ):
        """Test tracepath initial result item. Patching the tracepath loop
        to test multiple steps."""
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
        tracer.tracepath()

        # Retrieve trace result created from tracepath
        result = self.trace_manager.get_result(trace_id)

        self.assertEqual(result["request_id"], 111)
        self.assertEqual(len(result["result"]), 2)
        self.assertEqual(result["result"][0]["type"], "starting")
        self.assertEqual(result["result"][0]["dpid"], dpid["dpid"])
        self.assertEqual(result["result"][0]["port"], dpid["in_port"])

        self.assertEqual(result["result"][1]["type"], "trace")
        self.assertEqual(
            result["result"][1]["dpid"], "00:00:00:00:00:00:00:03"
        )
        self.assertEqual(result["result"][1]["port"], 3)

        self.assertEqual(
            result["request"]["trace"]["switch"]["dpid"], dpid["dpid"]
        )
        self.assertEqual(
            result["request"]["trace"]["switch"]["in_port"], dpid["in_port"]
        )
        self.assertEqual(
            result["request"]["trace"]["eth"]["dl_vlan"], eth["dl_vlan"]
        )
        self.assertEqual(mock_color.call_count, 2)
        self.assertEqual(mock_switch_colors.call_count, 2)

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    @patch("napps.amlight.sdntrace.tracing.tracer.send_packet_out")
    def test_send_trace_probe(
        self,
        mock_send_packet_out,
        mock_trace_loop,
        mock_get_switch,
        mock_color,
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

        result = tracer.send_trace_probe(switch_obj, in_port, probe_pkt)

        mock_send_packet_out.assert_called_once()

        self.assertEqual(result[0]["dpid"], "00:00:00:00:00:00:00:01")
        self.assertEqual(result[0]["port"], 1)
        self.assertEqual(result[1], "fake_event_object")
        mock_color.assert_called_once()
        mock_switch_colors.assert_called_once()

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    @patch("napps.amlight.sdntrace.tracing.tracer.send_packet_out")
    def test_send_trace_probe_timeout(
        self,
        mock_send_packet_out,
        mock_trace_loop,
        mock_get_switch,
        mock_color,
        mock_switch_colors,
    ):
        """Test send_trace_probe with timeout."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"
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
        eth = {"dl_vlan": 100, "dl_type": 2048}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        trace_entries = self.trace_manager.is_entry_valid(entries)

        tracer = TracePath(self.trace_manager, trace_id, trace_entries)

        in_port = 1
        probe_pkt = MagicMock()

        result = tracer.send_trace_probe(switch_obj, in_port, probe_pkt)

        self.assertEqual(mock_send_packet_out.call_count, 3)

        self.assertEqual(result[0], "timeout")
        self.assertEqual(result[1], False)
        mock_color.assert_called_once()
        mock_switch_colors.assert_called_once()

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    def test_check_loop(self, mock_get_switch, mock_color, mock_switch_colors):
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
        mock_color.assert_called_once()
        mock_switch_colors.assert_called_once()
        self.assertEqual(result, True)

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    def test_check_loop_false(
        self, mock_get_switch, mock_color, mock_switch_colors
    ):
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
        mock_color.assert_called_once()
        mock_switch_colors.assert_called_once()
        self.assertEqual(result, 0)

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    def test_check_loop_port_different(
        self, mock_get_switch, mock_color, mock_switch_colors
    ):
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
        mock_color.assert_called_once()
        mock_switch_colors.assert_called_once()
        self.assertEqual(result, 0)

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    @patch("napps.amlight.sdntrace.tracing.tracer.prepare_next_packet")
    def test_tracepath_loop(
        self,
        mock_next_packet,
        mock_probe,
        mock_get_switch,
        mock_color,
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
        tracer.tracepath_loop(trace_entries, color, switch)
        result = tracer.trace_result

        mock_probe.assert_called_once()
        mock_color.assert_called_once()
        mock_switch_colors.assert_called_once()
        self.assertEqual(result[0]["type"], "trace")
        self.assertEqual(result[0]["dpid"], "00:00:00:00:00:00:00:01")

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    def test_tracepath_loop_timeout(
        self, mock_probe, mock_get_switch, mock_color, mock_switch_colors
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
        tracer.tracepath_loop(trace_entries, color, switch)

        result = tracer.trace_result

        mock_probe.assert_called_once()
        mock_color.assert_called_once()
        mock_switch_colors.assert_called_once()
        self.assertEqual(result[0]["type"], "last")
        self.assertEqual(result[0]["reason"], "done")
        self.assertEqual(result[0]["msg"], "none")

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    @patch("napps.amlight.sdntrace.shared.switches.Switches.get_switch")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    @patch("napps.amlight.sdntrace.tracing.tracer.prepare_next_packet")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.check_loop")
    def test_tracepath_loop_with_loop(
        self,
        mock_check_loop,
        mock_next_packet,
        mock_probe,
        mock_get_switch,
        mock_color,
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
        tracer.tracepath_loop(trace_entries, color, switch)
        result = tracer.trace_result

        mock_check_loop.assert_called_once()
        mock_next_packet.assert_not_called()
        mock_probe.assert_called_once()
        self.assertEqual(mock_get_switch.call_count, 3)
        mock_color.assert_called_once()
        mock_switch_colors.assert_called_once()

        self.assertEqual(result[0]["type"], "trace")
        self.assertEqual(result[0]["dpid"], "00:00:00:00:00:00:00:01")
