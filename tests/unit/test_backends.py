"""Test backends of13 module."""

from unittest.mock import MagicMock, patch
from napps.amlight.sdntrace.backends.openflow13 import send_packet_out


@patch("napps.amlight.sdntrace.backends.openflow13.of_msg_prio")
def test_send_packet_out(mock_of_msg_prio) -> None:
    """Test send_packet_out."""
    controller = MagicMock()
    send_packet_out(controller, MagicMock(), MagicMock(), MagicMock())
    assert controller.buffers.msg_out.put.call_count == 1
    assert mock_of_msg_prio.call_count == 1
