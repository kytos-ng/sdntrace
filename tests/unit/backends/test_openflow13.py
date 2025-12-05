""" Tests for /backends/openflow13.py """

from unittest.mock import MagicMock, patch, AsyncMock

from napps.amlight.sdntrace import settings
from napps.amlight.sdntrace.backends.openflow13 import (
    packet_in,
    send_packet_out,
)


# pylint: disable=too-many-public-methods, too-many-lines
class TestOpenflow13:
    """Unit tests for backends.openflow13 functions"""

    def test_packet_in_with_color(self):
        """Test packet in with color ee:ee:ee:ee:ee:01."""
        raw = b"\x00\x15\xaf\xd58\x98\xee\xee\xee\xee\xee\x01\x08\x00testdata"
        # Ethernet(destination='00:15:af:d5:38:98',
        #          source='ee:ee:ee:ee:ee:01', ether_type=0x800,
        #          data=b'testdata')
        packet_in_msg = MagicMock()
        packet_in_msg.data.value = raw
        packet_in_msg.in_port.value = 1

        event = MagicMock()
        event.source.switch = "ee:ee:ee:ee:ee:01"
        event.message.in_port = 1

        ethernet, in_port, switch = packet_in(event, packet_in_msg)

        assert ethernet.source.value == "ee:ee:ee:ee:ee:01"
        assert in_port == 1
        assert switch == "ee:ee:ee:ee:ee:01"

    def test_normal_packet_in(self):
        """Test packet in without color."""
        raw = b"\x00\x15\xaf\xd58\x98\x00\x1f:>\x9a\xcf\x08\x00testdata"
        # Ethernet(destination='00:15:af:d5:38:98',
        #          source='00:1f:3a:3e:9a:cf', ether_type=0x800,
        #          data=b'testdata')
        packet_in_msg = MagicMock()
        packet_in_msg.data.value = raw
        packet_in_msg.in_port.value = 1

        event = MagicMock()
        event.source.switch = "00:1f:3a:3e:9a:cf"

        ethernet, in_port, switch = packet_in(event, packet_in_msg)

        assert ethernet == 0
        assert in_port == 0
        assert switch == 0

    def test_packet_out_with_color(self):
        """Test packet in with color ee:ee:ee:ee:ee:01."""
        data = b"\x00\x15\xaf\xd58\x98\xee\xee\xee\xee\xee\x01\x08\x00testdata"
        # Ethernet(destination='00:15:af:d5:38:98',
        #          source='ee:ee:ee:ee:ee:01', ether_type=0x800,
        #          data=b'testdata')
        controller = AsyncMock()
        switch = MagicMock()
        switch.connection.value = "00:15:af:d5:38:98"
        port = 1

        send_packet_out(controller, switch, port, data)

        # Verify that the controller sent the packet_out
        controller.buffers.msg_out.put.assert_called_once()
        called_event = controller.buffers.msg_out.put.call_args.args[0]

        # Verify the packet_out values
        assert called_event.name == "kytos/of_lldp.messages.out.ofpt_packet_out"
        assert called_event.content["destination"].value == switch.connection.value
        assert called_event.content["message"].in_port == port
        assert called_event.content["message"].data == data
        assert called_event.content["message"].actions[0].port == settings.OFPP_TABLE_13

    @patch("napps.amlight.sdntrace.backends.openflow13.of_msg_prio")
    def test_send_packet_out(self, mock_of_msg_prio) -> None:
        """Test send_packet_out."""
        controller = AsyncMock()
        send_packet_out(controller, MagicMock(), MagicMock(), MagicMock())
        assert controller.buffers.msg_out.put.call_count == 1
        assert mock_of_msg_prio.call_count == 1
