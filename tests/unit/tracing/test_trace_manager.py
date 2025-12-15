"""
    Test tracing.trace_manager
"""

import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from janus import Queue
from kytos.lib.helpers import (
    get_controller_mock,
    get_interface_mock,
    get_link_mock,
    get_switch_mock,
)
from pyof.foundation.network_types import Ethernet
from napps.amlight.sdntrace import settings
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.tracing.trace_entries import TraceEntries
from napps.amlight.sdntrace.tracing.trace_manager import TraceManager


# pylint: disable=protected-access
class TestTraceManager:
    """Unit tests for tracing.trace_manager.TraceManager"""

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
        self.create_basic_switches(get_controller_mock())
        TraceManager.run_traces = MagicMock()
        self.trace_manager = TraceManager(controller=get_controller_mock())
        self.trace_manager._request_queue = AsyncMock()

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

    async def test_is_entry_invalid(self):
        """Test if the entry request does not have a valid switch."""
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "a", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = await self.trace_manager.is_entry_valid(entries)

        assert entry == "Unknown Switch"

    async def test_is_entry_empty_dpid(self):
        """Test if the entry request does not have a valid switch."""
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = await self.trace_manager.is_entry_valid(entries)

        assert entry == "Error: dpid allows [a-f], int, and :. Lengths: 1-16 and 23"

    async def test_is_entry_missing_dpid(self):
        """Test if the entry request with missing dpid."""
        eth = {"dl_vlan": 100}
        dpid = {}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = await self.trace_manager.is_entry_valid(entries)

        assert entry == "Error: dpid not provided"

    @patch("napps.amlight.sdntrace.shared.colors.Colors.aget_switch_color")
    async def test_is_entry_invalid_not_colored(self, mock_acolors):
        """Test if the entry request does not have a valid color."""
        mock_acolors.return_value = {}
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = await self.trace_manager.is_entry_valid(entries)
        assert entry == "Switch not Colored"

    @patch("napps.amlight.sdntrace.shared.colors.Colors.aget_switch_color")
    async def test_is_entry_valid(self, mock_acolors):
        """Test if the entry request is valid."""
        mock_acolors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}
        entry = await self.trace_manager.is_entry_valid(entries)
        assert entry.dpid == "00:00:00:00:00:00:00:01"

    @patch("napps.amlight.sdntrace.shared.colors.Colors.aget_switch_color")
    async def test_new_trace(self, mock_acolors):
        """Test trace manager new trace creation."""
        mock_acolors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = await self.trace_manager.is_entry_valid(entries)
        assert isinstance(trace_entries, TraceEntries)

        trace_id = await self.trace_manager.new_trace(trace_entries)
        assert trace_id == 30001

        # new_trace does not check duplicated request.
        trace_id = await self.trace_manager.new_trace(trace_entries)
        assert trace_id == 30002

    def test_get_id(self):
        """Test trace manager ID control."""
        trace_id = self.trace_manager.get_id()
        assert trace_id == 30001

        trace_id = self.trace_manager.get_id()
        assert trace_id == 30002

        trace_id = self.trace_manager.get_id()
        assert trace_id == 30003

    @patch("napps.amlight.sdntrace.shared.colors.Colors.aget_switch_color")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    async def test_trace_pending(self, mock_send_probe, mock_acolors):
        """Test trace manager tracing request."""
        mock_acolors.return_value = {
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

        trace_entries = await self.trace_manager.is_entry_valid(entries)
        assert isinstance(trace_entries, TraceEntries)

        trace_id = await self.trace_manager.new_trace(trace_entries)
        assert trace_id == 30001

        pending = self.trace_manager.number_pending_requests()
        assert pending == 1

        result = self.trace_manager.get_result(trace_id)
        assert result == {"msg": "trace pending"}

    def test_request_invalid_trace_id(self):
        """Test trace manager tracing request."""
        result = self.trace_manager.get_result("1234")
        assert result == {"msg": "unknown trace id"}

    def test_trace_in_process(self):
        """Test trace manager in process."""
        self.trace_manager._spawn_trace = MagicMock()
        trace_id = 30001
        self.trace_manager._running_traces[trace_id] = MagicMock()
        result = self.trace_manager.get_result(trace_id)
        assert result == {"msg": "trace in process"}

    # pylint: disable=unused-argument, too-many-locals
    @patch(
        "napps.amlight.sdntrace.tracing.trace_manager.TraceManager.is_tracing_running"
    )
    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors.aget_switch_color")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.send_trace_probe")
    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath_loop")
    async def test_get_result(
        self,
        mock_trace_loop,
        mock_send_probe,
        mock_colors,
        mock_acolors,
        mock_is_running,
    ):
        """Test tracemanager tracing request and resultS."""

        colors = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }
        mock_colors.return_value = colors
        mock_acolors.return_value = colors
        mock_send_probe.return_value = {
            "dpid": "00:00:00:00:00:00:00:01",
            "port": 1,
        }, ""
        mock_trace_loop.return_value = True

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth, "timeout": 0.1}
        entries = {"trace": switch}

        self.trace_manager._request_queue = Queue()
        self.trace_manager._is_tracing_running = True
        mock_is_running.side_effect = [True, False]
        trace_entries = await self.trace_manager.is_entry_valid(entries)
        trace_id = await self.trace_manager.new_trace(trace_entries)
        pending = self.trace_manager.number_pending_requests()

        trace_thread = threading.Thread(target=self.trace_manager._run_traces)
        trace_thread.start()
        # Waiting thread to start processing the request
        count = 0
        while pending == 1:
            result = self.trace_manager.get_result(trace_id)
            pending = self.trace_manager.number_pending_requests()
            await asyncio.sleep(0.1)
            count += 1
            if count > 30:
                pytest.fail("Timeout waiting to start processing trace")
                break

        count = 0
        result = self.trace_manager.get_result(trace_id)
        # Waiting thread to process the request
        while "msg" in result and result["msg"] == "trace in process":
            result = self.trace_manager.get_result(trace_id)
            await asyncio.sleep(0.1)
            count += 1
            if count > 30:
                pytest.fail("Timeout waiting to process trace")
                break
        self.trace_manager.stop_traces()
        trace_thread.join()
        assert result["request_id"] == 30001
        assert result["result"][0]["type"] == "starting"
        assert result["result"][0]["dpid"] == "00:00:00:00:00:00:00:01"
        assert result["result"][0]["port"] == 1
        assert result["result"][0]["time"] is not None
        assert result["start_time"] is not None
        assert result["total_time"] is not None
        assert result["request"]["trace"]["switch"]["dpid"] == "00:00:00:00:00:00:00:01"
        assert result["request"]["trace"]["switch"]["in_port"] == 1

    @patch("napps.amlight.sdntrace.shared.colors.Colors.aget_switch_color")
    async def test_duplicated_request(self, mock_colors):
        """Test trace manager new trace creation."""
        mock_colors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = await self.trace_manager.is_entry_valid(entries)
        assert isinstance(trace_entries, TraceEntries)

        trace_id = await self.trace_manager.new_trace(trace_entries)
        assert trace_id == 30001

        duplicated = self.trace_manager.avoid_duplicated_request(trace_entries)
        assert duplicated is True

    @patch("napps.amlight.sdntrace.shared.colors.Colors.aget_switch_color")
    async def test_avoid_duplicated_request(self, mock_colors):
        """Test trace manager new trace creation."""
        mock_colors.return_value = {
            "color_field": "dl_src",
            "color_value": "ee:ee:ee:ee:ee:01",
        }

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = await self.trace_manager.is_entry_valid(entries)
        assert isinstance(trace_entries, TraceEntries)

        trace_id = await self.trace_manager.new_trace(trace_entries)
        assert trace_id == 30001

        entries["trace"]["switch"]["dpid"] = "00:00:00:00:00:00:00:02"
        trace_entries = await self.trace_manager.is_entry_valid(entries)
        assert isinstance(trace_entries, TraceEntries)

        duplicated = self.trace_manager.avoid_duplicated_request(trace_entries)
        assert duplicated is False

    def test_limit_traces_reached(self):
        """Test trace manager limit for thread processing."""
        # filling the running traces array
        mocked_obj = MagicMock()
        for i in range(settings.PARALLEL_TRACES - 1):
            self.trace_manager._running_traces[i] = mocked_obj
            is_limit = self.trace_manager.limit_traces_reached()
            assert not is_limit

        self.trace_manager._running_traces[settings.PARALLEL_TRACES] = mocked_obj
        is_limit = self.trace_manager.limit_traces_reached()
        assert is_limit

    @patch("napps.amlight.sdntrace.tracing.tracer.TracePath.tracepath")
    def test_spawn_trace(self, mock_tracepath):
        """Test spawn trace."""
        # mock_tracepath
        trace_id = 0
        trace_entries = MagicMock()

        self.trace_manager._running_traces[0] = 9999

        self.trace_manager._spawn_trace(trace_id, trace_entries)
        self.trace_manager.add_result(trace_id, {"result": "ok"})
        mock_tracepath.assert_called_once()
        assert len(self.trace_manager._running_traces) == 0


class TestTraceManagerTheadTest:
    """Now, load all entries at once"""

    def setup_method(self):
        """Set up before each test method"""
        TraceManager.run_traces = MagicMock()
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
    async def test_run_traces(self, mock_trace_loop, mock_send_probe, mock_colors):
        """Test tracemanager tracing request and results."""
        self.trace_manager._async_loop = asyncio.get_running_loop()
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
        TraceEntries().load_entries(entries)

        trace_entries = self.trace_manager._request_queue = Queue()
        _ = await self.trace_manager.new_trace(trace_entries)

        trace_thread = threading.Thread(target=self.trace_manager._run_traces)
        with patch.object(
            TraceManager, "is_tracing_running", side_effect=self.run_trace_once
        ):
            trace_thread.start()
            trace_thread.join()

        assert self.trace_manager._request_queue.async_q.qsize() == 0
        assert self.trace_manager.number_pending_requests() == 0

    async def test_queue_probe_packet_error(self):
        """Test queue_probe_packet handle error."""
        self.trace_manager._trace_pkt_in = {30001: MagicMock()}
        self.trace_manager._trace_pkt_in[30001].async_q.put = AsyncMock()
        mock_msg = (
            b"\01\xca\xfe\xca\xfe\xca\xfe\xee\xee\xee\xee\xee\x01\x88\xa8\x00\x01"
            b"\x81\x00\x00\x01\x08\x00E\x00\x00{\x00\x00\x00\x00\xff\x00\xb7~\x01"
            b"\x01\x01\x01\x01\x01\x01\x02\x80\x04\x95\\\x00\x00\x00\x00\x00\x00"
            b"\x00\x8c(napps.amlight.sdntrace.tracing.trace_msg\x94\x8c\x08TraceMsg"
            b"\x94\x93\x94)\x81\x94}\x94(\x8c\x0b_request_id\x94M1u\x8c\x05_step"
            b"\x94K\x00ub."
        )
        eth = Ethernet()
        eth.unpack(mock_msg)
        await self.trace_manager.queue_probe_packet("event_mock", eth, 1, MagicMock())

        assert self.trace_manager._trace_pkt_in[30001].async_q.put.call_count == 0
