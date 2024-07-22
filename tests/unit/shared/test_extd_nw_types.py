"""Testing TCP and UPD struct packets"""

# pylint: disable=protected-access
from napps.amlight.sdntrace.shared.extd_nw_types import TCP, UDP
from pyof.foundation.network_types import IPv4


class TestTCP:
    """Test TCP"""

    def test_tcp_pack(self):
        """Test pack"""
        ip_pk = IPv4()
        ip_pk.source = "127.0.0.1"
        ip_pk.destination = "127.0.0.2"
        ip_pk.protocol = 6
        tcp_pk = TCP()
        tcp_pk.src_port = 1
        tcp_pk.dst_port = 2
        tcp_pk.seq = 11111
        tcp_pk.window = 43690
        tcp_pk.data = b"mocked"
        expected_pack = b"\x00\x01\x00\x02\x00\x00+g\x00\x00\x00"
        expected_pack += b"\x00P\x02\xaa\xaa\xa5\x85\x00\x00mocked"
        actual_pack = tcp_pk.pack(ip_pk)
        assert expected_pack == actual_pack

    def test_tcp_unpack(self):
        """Test unpack"""
        ip_pk = IPv4()
        ip_pk.source = "127.0.0.1"
        ip_pk.destination = "127.0.0.2"
        ip_pk.protocol = 6
        exp_pk = TCP()
        exp_pk.src_port = 1
        exp_pk.dst_port = 2
        exp_pk.seq = 11111
        exp_pk.window = 43690
        exp_pk.data = b"mocked"
        data = b"\x00\x01\x00\x02\x00\x00+g\x00\x00"
        data += b"\x00\x00P\x02\xaa\xaaz$\x00\x00mocked"
        actual_pk = TCP()
        actual_pk.unpack(data)
        assert actual_pk == exp_pk

    def test_tcp_update_checksum_ipv4(self):
        """Test _update_checksum with IPv4"""
        ip_pk = IPv4()
        ip_pk.source = "127.0.0.1"
        ip_pk.destination = "127.0.0.2"
        ip_pk.protocol = 6
        tcp_pk = TCP()
        tcp_pk.src_port = 1
        tcp_pk.dst_port = 2
        tcp_pk.seq = 11111
        tcp_pk.window = 43690
        tcp_pk.pack(ip_pk)
        assert tcp_pk.checksum == 56266

        prev_length = tcp_pk.length
        tcp_pk.data = b"mocked"
        tcp_pk.pack()
        assert tcp_pk.length == prev_length

    def test_tcp_value_by_16_bits(self):
        """Test _value_by_16_bits"""
        data = b"A word is 4 bytes"
        tcp_pk = TCP()
        actual_value = tcp_pk._value_by_16_bits(data)
        assert actual_value == 163130


class TestUDP:
    """Test UDP"""

    def test_udp_pack(self):
        """Test pack"""
        ip_pk = IPv4()
        ip_pk.source = "127.0.0.1"
        ip_pk.destination = "127.0.0.2"
        ip_pk.protocol = 17
        upd_pk = UDP()
        upd_pk.src_port = 1
        upd_pk.dst_port = 2
        upd_pk.data = b"mocked"
        expected_pack = b"\x00\x01\x00\x02\x00\x0e\xcb\x8cmocked"
        assert upd_pk.pack(ip_pk) == expected_pack

    def test_udp_unpack(self):
        """Test unpack"""
        ip_pk = IPv4()
        ip_pk.source = "127.0.0.1"
        ip_pk.destination = "127.0.0.2"
        ip_pk.protocol = 17
        exp_pk = UDP()
        exp_pk.src_port = 1
        exp_pk.dst_port = 2
        exp_pk.data = b"mocked"
        data = b"\x00\x01\x00\x02\x00\x08\xcb\x98mocked"
        actual_pk = UDP()
        actual_pk.unpack(data)
        assert actual_pk == exp_pk

    def test_udp_update_checksum_ipv4(self):
        """Test _update_checksum"""
        ip_pk = IPv4()
        ip_pk.source = "127.0.0.1"
        ip_pk.destination = "127.0.0.2"
        ip_pk.protocol = 17
        udp_pk = UDP()
        udp_pk.src_port = 1
        udp_pk.dst_port = 2
        udp_pk.data = b"mocked"
        udp_pk.pack(ip_pk)
        assert udp_pk.checksum == 52108

    def test_udp_value_by_16_bits(self):
        """Test _value_by_16_bits"""
        data = b"A word is 4 bytes"
        udp_pk = UDP()
        actual_value = udp_pk._value_by_16_bits(data)
        assert actual_value == 163130
