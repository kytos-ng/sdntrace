"""Set up for tests, automatically detected by pytest."""

from unittest.mock import MagicMock
import pytest
from napps.amlight.sdntrace.tracing.trace_manager import TraceManager


@pytest.fixture(autouse=True)
def mock_run_traces():
    """Mock get_running_loop to run tests."""
    TraceManager.run_traces = MagicMock()
