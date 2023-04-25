"""
    Test tracing.trace_entries
"""
from unittest import TestCase
from unittest.mock import MagicMock, patch
from pyof.foundation.network_types import Ethernet

from napps.amlight.sdntrace.tracing import trace_pkt
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.tracing.trace_entries import TraceEntries
from kytos.lib.helpers import (
    get_interface_mock,
    get_link_mock,
    get_switch_mock,
    get_controller_mock,
)


# pylint: disable=too-many-public-methods, too-many-lines, protected-access
class TestTracePkt(TestCase):
    """Test all combinations for DPID"""

    def setUp(self):
        self.create_basic_switches(get_controller_mock())

        # The decorator run_on_thread is patched, so methods that listen
        # for events do not run on threads while tested.
        # Decorators have to be patched before the methods that are
        # decorated with them are imported.
        patch("kytos.core.helpers.run_on_thread", lambda x: x).start()

        self.addCleanup(patch.stopall)

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

    def test_generate_trace_pkt_tcp(self):
        """Test trace manager new trace creation."""
        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = TraceEntries()
        trace_entries.load_entries(entries)
        r_id = 999

        # Coloring REST response
        color = {"color_value": "ee:ee:ee:ee:ee:01"}

        # new_trace does not check duplicated request.
        in_port, pkt = trace_pkt.generate_trace_pkt(trace_entries, color, r_id)

        self.assertEqual(entries["trace"]["switch"]["in_port"], in_port)
        self.assertEqual(
            pkt,
            b"\xca\xfe\xca\xfe\xca\xfe\xee\xee\xee\xee\xee"
            b"\x01\x81\x00\x00d\x08\x00E\x00\x00p\x00\x00"
            b"\x00\x00\xff\x00\xb7\x89\x01\x01\x01\x01\x01"
            b"\x01\x01\x02\x80\x04\x95Q\x00\x00\x00\x00\x00"
            b"\x00\x00\x8c(napps.amlight.sdntrace.tracing."
            b"trace_msg\x94\x8c\x08TraceMsg\x94\x93\x94)"
            b"\x81\x94}\x94\x8c\x0b_request_id\x94M\xe7"
            b"\x03sb.",
        )

    @patch("napps.amlight.sdntrace.shared.colors.Colors.get_switch_color")
    @patch("napps.amlight.sdntrace.shared.colors.Colors._get_colors")
    def test_get_node_color_from_dpid(self, mock_color, mock_switch_colors):
        """Test get color from dpid."""
        mock_switch_colors.return_value = "ee:ee:ee:ee:ee:01"

        switch, color = trace_pkt._get_node_color_from_dpid("00:00:00:00:00:00:00:01")

        self.assertEqual(switch.dpid, "00:00:00:00:00:00:00:01")
        self.assertEqual(color, "ee:ee:ee:ee:ee:01")
        mock_color.assert_called_once()
        mock_switch_colors.assert_called_once()

    def test_get_node_color_unknown_dpid(self):
        """Test get color from unknown dpid."""
        switch, color = trace_pkt._get_node_color_from_dpid("99:99:99:99:99:99:99:99")

        self.assertEqual(switch, 0)
        self.assertEqual(color, 0)

    def test_get_vlan_from_pkt(self):
        """Test get color from unknown dpid."""
        pkt = (
            b"\xca\xfe\xca\xfe\xca\xfe\xee\xee\xee\xee\xee"
            b"\x01\x81\x00\x00d\x08\x00E\x00\x00p\x00\x00"
            b"\x00\x00\xff\x00\xb7\x89\x01\x01\x01\x01\x01"
            b"\x01\x01\x02\x80\x04\x95Q\x00\x00\x00\x00\x00"
            b"\x00\x00\x8c(napps.amlight.sdntrace.tracing."
            b"trace_msg\x94\x8c\x08TraceMsg\x94\x93\x94)"
            b"\x81\x94}\x94\x8c\x0b_request_id\x94M\xe7"
            b"\x03sb."
        )

        vid = trace_pkt._get_vlan_from_pkt(pkt)

        self.assertEqual(vid, 100)

    def test_process_packet(self):
        """Test process packet to find the trace message."""
        pkt = (
            b"\xca\xfe\xca\xfe\xca\xfe\xee\xee\xee\xee\xee"
            b"\x01\x81\x00\x00d\x08\x00E\x00\x00p\x00\x00"
            b"\x00\x00\xff\x00\xb7\x89\x01\x01\x01\x01\x01"
            b"\x01\x01\x02\x80\x04\x95Q\x00\x00\x00\x00\x00"
            b"\x00\x00\x8c(napps.amlight.sdntrace.tracing."
            b"trace_msg\x94\x8c\x08TraceMsg\x94\x93\x94)"
            b"\x81\x94}\x94\x8c\x0b_request_id\x94M\xe7"
            b"\x03sb."
        )
        expected = (
            b"\x80\x04\x95Q\x00\x00\x00\x00\x00"
            b"\x00\x00\x8c(napps.amlight.sdntrace.tracing."
            b"trace_msg\x94\x8c\x08TraceMsg\x94\x93\x94)"
            b"\x81\x94}\x94\x8c\x0b_request_id\x94M\xe7"
            b"\x03sb."
        )

        ethernet = Ethernet()
        ethernet.unpack(pkt)

        trace_msg = trace_pkt.process_packet(ethernet)
        self.assertEqual(trace_msg, expected)

    @patch("napps.amlight.sdntrace.tracing.trace_pkt._get_node_color_from_dpid")
    def test_prepare_next_packet(self, mock_get_color):
        """Test trace prepare next packet."""
        color_switch = MagicMock()
        color_switch.dpid = "00:00:00:00:00:00:00:01"
        mock_get_color.return_value = [color_switch, "ee:ee:ee:ee:ee:01"]

        eth = {"dl_vlan": 100}
        dpid = {"dpid": "00:00:00:00:00:00:00:01", "in_port": 1}
        switch = {"switch": dpid, "eth": eth}
        entries = {"trace": switch}

        trace_entries = TraceEntries()
        trace_entries.load_entries(entries)

        raw = (
            b"\xca\xfe\xca\xfe\xca\xfe\xee\xee\xee\xee\xee"
            b"\x01\x81\x00\x00d\x08\x00E\x00\x00p\x00\x00"
            b"\x00\x00\xff\x00\xb7\x89\x01\x01\x01\x01\x01"
            b"\x01\x01\x02\x80\x04\x95Q\x00\x00\x00\x00\x00"
            b"\x00\x00\x8c(napps.amlight.sdntrace.tracing."
            b"trace_msg\x94\x8c\x08TraceMsg\x94\x93\x94)"
            b"\x81\x94}\x94\x8c\x0b_request_id\x94M\xe7"
            b"\x03sb."
        )

        packet_in_msg = MagicMock()
        packet_in_msg.data.value = raw
        packet_in_msg.in_port.value = 1
        packet_in_msg.header.version = 1

        event = MagicMock()
        event.source.switch = "00:00:00:00:00:00:00:02"
        event.content = {"message": packet_in_msg}

        pkt_in = {
            "dpid": "00:00:00:00:00:00:00:01",
            "in_port": 1,
            "msg": "",
            "ethernet": "",
            "event": event,
        }
        result = {"dpid": pkt_in["dpid"], "port": pkt_in["in_port"]}

        # result = [result_trace, result_color, result_switch]
        result = trace_pkt.prepare_next_packet(trace_entries, result, event)

        self.assertEqual(result[0], trace_entries)
        self.assertEqual(result[1], mock_get_color()[1])
        self.assertEqual(result[2].dpid, color_switch.dpid)
