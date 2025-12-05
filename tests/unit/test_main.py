"""Module to test the main napp file."""

import asyncio
from unittest.mock import patch, MagicMock
from napps.amlight.sdntrace import settings
from napps.amlight.sdntrace.tracing.trace_entries import TraceEntries
from kytos.lib.helpers import get_controller_mock, get_test_client


# pylint: disable=too-many-public-methods, too-many-lines
class TestMain:
    """Test the Main class."""

    def setup_method(self):
        """Execute steps before each tests."""

        # The decorator run_on_thread is patched, so methods that listen
        # for events do not run on threads while tested.
        # Decorators have to be patched before the methods that are
        # decorated with them are imported.
        patch("kytos.core.helpers.run_on_thread", lambda x: x).start()
        # pylint: disable=import-outside-toplevel
        from napps.amlight.sdntrace.main import Main

        Main.get_eline_controller = MagicMock()
        self.controller = get_controller_mock()
        self.napp = Main(self.controller)
        self.api_client = get_test_client(self.controller, self.napp)
        self.base_endpoint = "amlight/sdntrace/v1"

    @patch(
        "napps.amlight.sdntrace.tracing.trace_manager.TraceManager.avoid_duplicated_request"
    )
    @patch("napps.amlight.sdntrace.tracing.trace_manager.TraceManager.is_entry_valid")
    @patch("napps.amlight.sdntrace.tracing.trace_manager.TraceManager.new_trace")
    async def test_run_trace(self, mock_trace, mock_entry, mock_duplicate):
        """Test run_trace"""
        self.napp.controller.loop = asyncio.get_running_loop()
        payload = {
            "trace": {
                "switch": {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1},
                "eth": {"dl_vlan": 400, "dl_vlan_pcp": 4, "dl_type": 2048},
            }
        }
        # Error not TraceEntries instance
        mock_entry.return_value = "not_entry"
        url = f"{self.base_endpoint}/trace"
        response = await self.api_client.put(url, json=payload)
        assert response.status_code == 200
        actual_result = response.json()
        expected_result = {"result": {"error": "not_entry"}}
        assert actual_result == expected_result

        # Error duplicated trace
        mock_entry.return_value = TraceEntries()
        mock_duplicate.return_value = True
        url = f"{self.base_endpoint}/trace"
        response = await self.api_client.put(url, json=payload)
        assert response.status_code == 200
        result = response.json()
        assert result["result"]["error"] == "Duplicated Trace Request ignored"

        # Success
        mock_duplicate.return_value = False
        trace_id = 9999
        mock_trace.return_value = trace_id
        url = f"{self.base_endpoint}/trace"
        response = await self.api_client.put(url, json=payload)
        assert response.status_code == 200
        result = response.json()
        assert result["result"]["trace_id"] == trace_id

    @patch("napps.amlight.sdntrace.tracing.trace_manager.TraceManager.get_results")
    async def test_get_results(self, mock_rest_results):
        """Test get_results"""
        mock_rest_results.return_value = "mock_results"
        url = f"{self.base_endpoint}/trace"
        response = await self.api_client.get(url)
        assert response.status_code == 200
        result = response.json()
        assert result == "mock_results"
        assert mock_rest_results.call_count == 1

    # pylint: disable=protected-access
    async def test_get_result(self):
        """Test get_result"""
        trace_id = "9999"

        # Trace in process
        self.napp.tracing._results_queue = {}
        self.napp.tracing._running_traces = {int(trace_id): "mock"}
        url = f"{self.base_endpoint}/trace/{trace_id}"
        response = await self.api_client.get(url)
        assert response.status_code == 200
        result = response.json()
        assert result == {"msg": "trace in process"}

        # Trace pending
        self.napp.tracing._running_traces = {}
        self.napp.tracing._request_dict = {int(trace_id): "mock"}
        url = f"{self.base_endpoint}/trace/{trace_id}"
        response = await self.api_client.get(url)
        assert response.status_code == 200
        result = response.json()
        assert result == {"msg": "trace pending"}

        # Trace not found
        self.napp.tracing._request_dict = {}
        url = f"{self.base_endpoint}/trace/{int(trace_id)}"
        response = await self.api_client.get(url)
        assert response.status_code == 200
        result = response.json()
        assert result == {"msg": "unknown trace id"}

        # Success
        self.napp.tracing._results_queue = {int(trace_id): "success_mock"}
        url = f"{self.base_endpoint}/trace/{trace_id}"
        response = await self.api_client.get(url)
        assert response.status_code == 200
        result = response.json()
        assert result == "success_mock"

    # pylint: disable=protected-access
    @patch("napps.amlight.sdntrace.tracing.trace_manager.new_thread")
    async def test_get_stats(self, mock_thread):
        """Test get_stats"""
        mock_thread.return_value = True
        traces_n = 99
        self.napp.tracing.stop_traces()
        traces_running = {"mock": "request"}
        dict_request = {"mock1": "trace1", "mock2": "trace2"}
        queue_result = {"mock": "result"}
        self.napp.tracing._total_traces_requested = traces_n
        self.napp.tracing._running_traces = traces_running
        self.napp.tracing._request_dict = dict_request
        self.napp.tracing._results_queue = queue_result
        url = f"{self.base_endpoint}/stats"
        response = await self.api_client.get(url)
        assert response.status_code == 200
        actual_result = response.json()
        expected_result = {
            "number_of_requests": traces_n,
            "number_of_running_traces": len(traces_running),
            "number_of_pending_traces": len(dict_request),
            "list_of_pending_traces": queue_result,
        }
        assert actual_result == expected_result

    async def test_list_settings(self):
        """Test list_settings"""
        url = f"{self.base_endpoint}/settings"
        response = await self.api_client.get(url)
        actual_result = response.json()
        expected_result = {
            "color_field": settings.COLOR_FIELD,
            "color_value": settings.COLOR_VALUE,
            "parallel_traces": settings.PARALLEL_TRACES,
        }
        assert actual_result == expected_result
