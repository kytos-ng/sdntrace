"""
    Test tracing.trace_manager
"""
import time
from unittest import TestCase
from unittest.mock import patch, MagicMock

from napps.amlight.sdntrace import settings
from napps.amlight.sdntrace.tracing.trace_manager import TraceManager
from napps.amlight.sdntrace.tracing.trace_entries import TraceEntries
from napps.amlight.sdntrace.shared.switches import Switches

from kytos.lib.helpers import (
    get_interface_mock,
    get_link_mock,
    get_switch_mock,
    get_controller_mock,
)


# pylint: disable=protected-access
class TestTraceManager(TestCase):
    """Unit tests for tracing.trace_manager.TraceManager"""

    def setUp(self):
        self.create_basic_switches(get_controller_mock())

        # The decorator run_on_thread is patched, so methods that listen
        # for events do not run on threads while tested.
        # Decorators have to be patched before the methods that are
        # decorated with them are imported.
        patch("kytos.core.helpers.run_on_thread", lambda x: x).start()

        self.addCleanup(patch.stopall)
        self.trace_manager = TraceManager(controller=get_controller_mock())

    def tearDown(self) -> None:
        self.trace_manager.stop_traces()
        return super().tearDown()

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

        Switches(MagicMock())._switches = controller.switches

    def test_is_entry_invalid(self):
        """Test if the entry request does not have a valid switch."""
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "a", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = self.trace_manager.is_entry_valid(entries)

        self.assertEqual(entry, "Unknown Switch")

    def test_is_entry_empty_dpid(self):
        """Test if the entry request does not have a valid switch."""
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = self.trace_manager.is_entry_valid(entries)

        self.assertEqual(
            entry, "Error: dpid allows [a-f], int, and :. Lengths: 1-16 and 23"
        )

    def test_is_entry_missing_dpid(self):
        """Test if the entry request with missing dpid."""
        eth = {"dl_vlan": 100}
        dpid = {}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = self.trace_manager.is_entry_valid(entries)

        self.assertEqual(entry, "Error: dpid not provided")

    def test_is_entry_invalid_not_colored(self):
        """Test if the entry request does not have a valid color."""
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = self.trace_manager.is_entry_valid(entries)
        self.assertEqual(entry, "Switch not Colored")

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    def test_is_entry_valid(self, mock_colors):
        """Test if the entry request is valid."""
        mock_colors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = self.trace_manager.is_entry_valid(entries)
        self.assertEqual(entry.dpid, "00:00:00:00:00:00:00:01")

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    def test_new_trace(self, mock_colors):
        """Test trace manager new trace creation."""
        mock_colors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = self.trace_manager.is_entry_valid(entries)
        self.assertIsInstance(trace_entries, TraceEntries)

        trace_id = self.trace_manager.new_trace(trace_entries)
        self.assertEqual(trace_id, 30001)

        # new_trace does not check duplicated request.
        trace_id = self.trace_manager.new_trace(trace_entries)
        self.assertEqual(trace_id, 30002)

    def test_get_id(self):
        """Test trace manager ID control."""
        trace_id = self.trace_manager.get_id()
        self.assertEqual(trace_id, 30001)

        trace_id = self.trace_manager.get_id()
        self.assertEqual(trace_id, 30002)

        trace_id = self.trace_manager.get_id()
        self.assertEqual(trace_id, 30003)

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    def test_trace_pending(self, mock_send_probe, mock_colors):
        """Test trace manager tracing request."""
        mock_colors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }
        mock_send_probe.return_value = {
            "dpid": "00:00:00:00:00:00:00:01",
            "port": 1,
        }, ""

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = self.trace_manager.is_entry_valid(entries)
        self.assertIsInstance(trace_entries, TraceEntries)

        trace_id = self.trace_manager.new_trace(trace_entries)
        self.assertEqual(trace_id, 30001)

        pending = self.trace_manager.number_pending_requests()
        self.assertEqual(pending, 1)

        result = self.trace_manager.get_result(trace_id)
        self.assertEqual(result, {"msg": "trace pending"})

    def test_request_invalid_trace_id(self):
        """Test trace manager tracing request."""
        result = self.trace_manager.get_result("1234")
        self.assertEqual(result, {"msg": "unknown trace id"})

    def test_trace_in_process(self):
        """Test trace manager in process."""
        self.trace_manager._spawn_trace = MagicMock()
        trace_id = 30001
        self.trace_manager._running_traces[trace_id] = {}
        result = self.trace_manager.get_result(trace_id)
        assert result == {"msg": "trace in process"}

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    def test_get_result(self, mock_trace_loop, mock_send_probe, mock_colors):
        """Test tracemanager tracing request and resultS."""
        mock_colors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }
        mock_send_probe.return_value = {
            "dpid": "00:00:00:00:00:00:00:01",
            "port": 1,
        }, ""
        mock_trace_loop.return_value = True

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = self.trace_manager.is_entry_valid(entries)
        trace_id = self.trace_manager.new_trace(trace_entries)
        pending = self.trace_manager.number_pending_requests()

        # Waiting thread to start processing the request
        count = 0
        while pending == 1:
            result = self.trace_manager.get_result(trace_id)
            pending = self.trace_manager.number_pending_requests()
            time.sleep(0.1)
            count += 1
            if count > 30:
                self.fail("Timeout waiting to start processing trace")
                break

        count = 0
        result = self.trace_manager.get_result(trace_id)
        # Waiting thread to process the request
        while "msg" in result and result["msg"] == "trace in process":
            result = self.trace_manager.get_result(trace_id)
            time.sleep(0.1)
            count += 1
            if count > 30:
                self.fail("Timeout waiting to process trace")
                break

        self.assertEqual(result["request_id"], 30001)
        self.assertEqual(result["result"][0]["type"], "starting")
        self.assertEqual(
            result["result"][0]["dpid"], "00:00:00:00:00:00:00:01"
        )
        self.assertEqual(result["result"][0]["port"], 1)
        self.assertIsNotNone(result["result"][0]["time"])
        self.assertIsNotNone(result["start_time"])
        self.assertIsNotNone(result["total_time"])
        self.assertEqual(
            result["request"]["trace"]["switch"]["dpid"],
            "00:00:00:00:00:00:00:01",
        )
        self.assertEqual(result["request"]["trace"]["switch"]["in_port"], 1)

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    def test_duplicated_request(self, mock_colors):
        """Test trace manager new trace creation."""
        mock_colors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = self.trace_manager.is_entry_valid(entries)
        self.assertIsInstance(trace_entries, TraceEntries)

        trace_id = self.trace_manager.new_trace(trace_entries)
        self.assertEqual(trace_id, 30001)

        duplicated = self.trace_manager.avoid_duplicated_request(trace_entries)
        self.assertEqual(duplicated, True)

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    def test_avoid_duplicated_request(self, mock_colors):
        """Test trace manager new trace creation."""
        mock_colors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = self.trace_manager.is_entry_valid(entries)
        self.assertIsInstance(trace_entries, TraceEntries)

        trace_id = self.trace_manager.new_trace(trace_entries)
        self.assertEqual(trace_id, 30001)

        entries["trace"]["switch"]["dpid"] = "00:00:00:00:00:00:00:02"
        trace_entries = self.trace_manager.is_entry_valid(entries)
        self.assertIsInstance(trace_entries, TraceEntries)

        duplicated = self.trace_manager.avoid_duplicated_request(trace_entries)
        self.assertEqual(duplicated, False)

    def test_limit_traces_reached(self):
        """Test trace manager limit for thread processing."""
        # filling the running traces array
        for i in range(settings.PARALLEL_TRACES - 1):
            self.trace_manager._running_traces[i] = i
            is_limit = self.trace_manager.limit_traces_reached()
            self.assertFalse(is_limit)

        self.trace_manager._running_traces[settings.PARALLEL_TRACES] = 9999
        is_limit = self.trace_manager.limit_traces_reached()
        self.assertTrue(is_limit)

    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath")
    def test_spawn_trace(self, mock_tracepath):
        """Test spawn trace."""
        # mock_tracepath
        trace_id = 0
        trace_entries = MagicMock()

        self.trace_manager._running_traces[0] = 9999

        self.trace_manager._spawn_trace(trace_id, trace_entries)

        mock_tracepath.assert_called_once()
        self.assertEqual(len(self.trace_manager._running_traces), 0)


class TestTraceManagerTheadTest(TestCase):
    """Now, load all entries at once"""

    def setUp(self):

        # The decorator run_on_thread is patched, so methods that listen
        # for events do not run on threads while tested.
        # Decorators have to be patched before the methods that are
        # decorated with them are imported.
        patch("kytos.core.helpers.run_on_thread", lambda x: x).start()
        # pylint: disable=import-outside-toplevel
        self.addCleanup(patch.stopall)

        self.trace_manager = TraceManager(controller=get_controller_mock())
        self.trace_manager.stop_traces()

        self.count_running_traces = 0

    def run_trace_once(self):
        """function to replace the <flag> in "while <flag>()" code
        to run the loop just once."""
        if self.count_running_traces == 0:
            self.count_running_traces = self.count_running_traces + 1
            return True
        return False

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    def test_run_traces(self, mock_trace_loop, mock_send_probe, mock_colors):
        """Test tracemanager tracing request and results."""
        mock_colors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }
        mock_send_probe.return_value = {
            "dpid": "00:00:00:00:00:00:00:01",
            "port": 1,
        }, ""
        mock_trace_loop.return_value = True

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = self.trace_manager.is_entry_valid(entries)

        self.trace_manager._request_queue[1] = trace_entries

        with patch.object(
            TraceManager, "is_tracing_running", side_effect=self.run_trace_once
        ):
            self.trace_manager._run_traces(0.5)

        self.assertEqual(len(self.trace_manager._request_queue), 0)
        self.assertEqual(self.trace_manager.number_pending_requests(), 0)
