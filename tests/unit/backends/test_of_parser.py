""" Tests for /backends/of_parser.py """

from unittest.mock import MagicMock, patch

from napps.amlight.sdntrace.backends.of_parser import (
    process_packet_in,
    send_packet_out,
)


# pylint: disable=too-many-public-methods, too-many-lines
class TestOFParser:
    """Unit tests for backends.of_parser functions"""

    def test_process_packet_in(self):
        """Test process packet in for openflow13 with data."""
        raw = b"\x00\x15\xaf\xd58\x98\xee\xee\xee\xee\xee\x01\x08\x00testdata"
        # Ethernet(destination='00:15:af:d5:38:98',
        #          source='ee:ee:ee:ee:ee:01', ether_type=0x800,
        #          data=b'testdata')
        packet_in_msg = MagicMock()
        packet_in_msg.data.value = raw

        event = MagicMock()
        event.source.switch = "ee:ee:ee:ee:ee:01"
        event.content = {"message": packet_in_msg}
        event.content["message"].header.version.value = 4
        event.message.in_port = 1

        ethernet, in_port, switch = process_packet_in(event)

        assert ethernet.source.value == "ee:ee:ee:ee:ee:01"
        assert in_port == 1
        assert switch == "ee:ee:ee:ee:ee:01"

    @patch("napps.amlight.sdntrace.backends.openflow13.packet_in")
    def test_process_of13_packet_in_patched(self, mock_of13_packet_in):
        """Test process packet in for openflow13."""

        event = MagicMock()
        event.content = {"message": MagicMock()}
        event.content["message"].header.version.value = 4

        process_packet_in(event)

        mock_of13_packet_in.assert_called_once()

    @patch("napps.amlight.sdntrace.backends.openflow13.packet_in")
    def test_process_packet_in_error(self, mock_of13_packet_in):
        """Test process packet in for openflow13."""

        event = MagicMock()
        event.content = {"message": MagicMock()}
        event.content["message"].header.version.value = 9999

        ethernet, in_port, switch = process_packet_in(event)

        assert ethernet == 0
        assert in_port == 0
        assert switch == 0

        mock_of13_packet_in.assert_not_called()

    @patch("napps.amlight.sdntrace.backends.openflow13.send_packet_out")
    async def test_process_of13_packet_out_patched(self, mock_of13_packet_out):
        """Test process packet out for openflow13."""
        controller = MagicMock()
        switch = MagicMock()
        switch.features.header.version.value = 4

        port = MagicMock()
        data = MagicMock()

        await send_packet_out(controller, switch, port, data)

        mock_of13_packet_out.assert_called_once()

    @patch("napps.amlight.sdntrace.backends.openflow13.send_packet_out")
    async def test_process_packet_out_error(self, mock_of13_packet_out):
        """Test process packet out for openflow13."""
        controller = MagicMock()
        switch = MagicMock()
        switch.features.header.version.value = 999

        port = MagicMock()
        data = MagicMock()

        await send_packet_out(controller, switch, port, data)

        mock_of13_packet_out.assert_not_called()
