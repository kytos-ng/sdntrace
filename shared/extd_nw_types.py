"""Extends Network packet types.

Defines and Implements Basic Network packet types, such as TCP and UDP.
"""

from pyof.foundation.network_types import IPv4, IPv6
from pyof.foundation.base import GenericStruct
from pyof.foundation.basic_types import BinaryData, UBInt16, UBInt32
from typing import Union
from random import randrange

__all__ = ('TCP', 'UDP')


class TCP(GenericStruct):
    """TCP packet"""

    src_port = UBInt16()
    dst_port = UBInt16()
    seq = UBInt32()
    ack = UBInt32()
    _length_flags = UBInt16()
    window = UBInt16()
    checksum = UBInt16()
    urgent_pointer = UBInt16()
    options = BinaryData()
    data = BinaryData()

    def __init__(self, src_port=0, dst_port=0, seq=0, ack=0, length=5,
                 flags=2, window=83, checksum=0, urgent_pointer=0, options=b'', data=b''):
        """
        These default values are considering this TCP message is first sent, initiating
         handshake.

        Args:
            src_port(int): Source port. Defaults to 0
            dst_port(int): Destination port. Defaults to 0
            seq(int): Sequence number (raw). Random number [0, 4294967296]
            ack(int): Acknowledgment number (raw). Defaults to 0
            length(int): Header length, data offset. Defaults(minimun) to 5 words
            flags(bits): Flags. Defaults to 2 or 0000 0000 0010. Divided in:
                reserved: Reserved, not used yet. Defaults to 000
                ecn_acc: Accurate ECN. Defaults to 0
                cwr: Congestion window reduced. Defaults to 0
                ecn_echo: ECN-Echo. Defaults to 0
                urgent: Urgent. Defaults to 0
                ack: Acknoledgment. Defaults to 0
                push: Push. Defaults to 0
                reset: Reset. Defaults to 0
                syn: Syn. Defaults to 1
                fin: Fin. Defaults to 0
            window(int): Window. Defaults to 0
            checksum(int): Checksum. Defaults to 0
            urgent_pointer(int): Urgent pointer. Defaults to 0
            options(bytes): Options. Defaults to empty bytes
            data(bytes): Data. Defaults to empty bytes

        TCP Header Format:
             0                   1                   2                   3
             0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 
            +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
            |          Source Port          |       Destination Port        |
            +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
            |                        Sequence Number                        |
            +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
            |                    Acknowledgment Number                      |
            +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
            |  Data |     |A|C|E|U|A|P|R|S|F|                               |
            | Offset| RSV |C|W|C|R|C|S|S|Y|I|            Window             |
            |       |     |C|R|H|G|K|H|T|N|N|                               |
            +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
            |           Checksum            |         Urgent Pointer        |
            +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
            |                    Options                    |    Padding    |
            +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
            |                             data                              |
            +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        """
        super().__init__()
        self.src_port = src_port
        self.dst_port = dst_port
        self.seq = seq if seq != 0 else randrange(4294967296)
        self.ack = ack
        self.length = length
        self.flags = flags
        self.window = window
        self.checksum = checksum
        self.urgent_pointer = urgent_pointer
        self.options = options
        self.data = data

    def _value_by_16_bits(self, value: bytes) -> int:
        """Calculate the integer value of the argument partitioned by 2 bytes."""
        total = 0
        while value:
            total = total + int.from_bytes(value[-2:])
            value = value[:-2]
        return total

    def _update_checksum(self, ip_header:Union[IPv4, IPv6]=None):
        """Update the packet checksum to enable integrity check.
         Each addend is 16 bits."""
        self.length = 5 + (len(self.options) // 4)
        self._length_flags = self.length << 12 | self.flags

        sequence_hex = f'{self.seq:08x}'
        acknowledgment_hex = f'{self.ack:08x}'
        sequence_upper = int(sequence_hex[:4] or '0', 16)
        sequence_lower = int(sequence_hex[-4:] or '0', 16)
        acknowledgment_upper = int(acknowledgment_hex[:4] or '0', 16)
        acknowledgment_lower = int(acknowledgment_hex[-4:] or '0', 16)

        if isinstance(ip_header, IPv4):
            source_list = [int(octet) for octet in ip_header.source.split(".")]
            destination_list = [int(octet) for octet in
                                ip_header.destination.split(".")]
            source_upper = (source_list[0] << 8) + source_list[1]
            source_lower = (source_list[2] << 8) + source_list[3]
            destination_upper = (destination_list[0] << 8) + destination_list[1]
            destination_lower = (destination_list[2] << 8) + destination_list[3]
            ip_value = (source_upper + source_lower + destination_upper +
                        destination_lower + ip_header.protocol + (self.length * 4) + len(self.data))
        else:
            # TODO: Implement IPv6 header analysis
            ip_value = 0

        block_sum = (self.src_port + self.dst_port + sequence_upper +
                         sequence_lower + acknowledgment_upper + acknowledgment_lower +
                         self._length_flags + self.window + 0 + self.urgent_pointer +
                         self._value_by_16_bits(self.options) +
                         self._value_by_16_bits(self.data) + ip_value)
        
        while block_sum > 65535:
            carry = block_sum >> 16
            block_sum = (block_sum & 65535) + carry

        self.checksum = ~block_sum & 65535

    def pack(self, ip_header:Union[IPv4, IPv6]=None, value=None):
        """Pack the struct in a binary representation.

        Merge some fields to ensure correct packing.

        Returns:
            bytes: Binary representation of this instance.

        """
        self._update_checksum(ip_header)
        return super().pack(value)
    
    def unpack(self, buff:bytes, offset=0):
        """Unpack a binary struct into this object's attributes.

        Return the values instead of the lib's basic types.

        Args:
            buff (bytes): Binary buffer.
            offset (int): Where to begin unpacking.

        Raises:
            :exc:`~.exceptions.UnpackException`: If unpack fails.

        """
        super().unpack(buff, offset)
        self.src_port = self.src_port.value
        self.dst_port = self.dst_port.value
        self.seq = self.seq.value
        self.ack = self.ack.value
        self.length = self._length_flags.value >> 12
        self.flags = self._length_flags.value & 4095
        self.window = self.window.value
        self.checksum = self.checksum.value

        if self.length > 5:
            option_size = (self.length - 5) * 4
            self.data = self.options.value[option_size:]
            self.options = self.options.value[:option_size]
        else:
            self.data = self.options.value
            self.options = b''


class UDP(GenericStruct):
    """ UDP packet"""

    src_port = UBInt16()
    dst_port = UBInt16()
    length = UBInt16()
    checksum = UBInt16()
    data = BinaryData()
    
    def __init__(self, src_port=0, dst_port=0, length=0, checksum=0, data=b''):
        """Create an UDP header with default values.

        Args:
            src_port(int): Source port. Defaults to 0
            dst_port(int): Destination port. Defaults to 0
            length(int): Length. Defaults to 8 (minimum in bytes)
            checksum(int): Checksum. Defaults to 0
            data(bytes): Data. Defults to empty bytes

        User Datagram Header Format:

             0      7 8     15 16    23 24    31
            +--------+--------+--------+--------+
            |     Source      |   Destination   |
            |      Port       |      Port       |
            +--------+--------+--------+--------+
            |                 |                 |
            |     Length      |    Checksum     |
            +--------+--------+--------+--------+
            |
            |          data octets ...
            +---------------- ...
        """
        self.src_port = src_port
        self.dst_port = dst_port
        self.length = length
        self.checksum = checksum
        self.data = data

    def _value_by_16_bits(self, value: bytes) -> int:
        """Calculate the integer value of the argument partitioned by 2 bytes."""
        total = 0
        while value:
            total = total + int.from_bytes(value[-2:])
            value = value[:-2]
        return total

    def _update_checksum(self, ip_header:Union[IPv4, IPv6]=None):
        """Update the packet checksum to enable integrity check.
         Each addend is 16 bits."""
        self.length = 8 + len(self.data)

        if isinstance(ip_header, IPv4):
            source_list = [int(octet) for octet in ip_header.source.split(".")]
            destination_list = [int(octet) for octet in
                                ip_header.destination.split(".")]
            source_upper = (source_list[0] << 8) + source_list[1]
            source_lower = (source_list[2] << 8) + source_list[3]
            destination_upper = (destination_list[0] << 8) + destination_list[1]
            destination_lower = (destination_list[2] << 8) + destination_list[3]
            ip_value = (source_upper + source_lower + destination_upper +
                        destination_lower + ip_header.protocol + self.length)
        else:
            # TODO: Implement IPv6 header analysis
            ip_value = 0

        block_sum = ip_value + self.src_port + self.dst_port + self.length + self._value_by_16_bits(self.data)

        while block_sum > 65535:
            carry = block_sum >> 16
            block_sum = (block_sum & 65535) + carry

        self.checksum = ~block_sum & 65535

    def pack(self, ip_header:Union[IPv4, IPv6]=None, value=None):
        """Pack the struct in a binary representation.

        Merge some fields to ensure correct packing.

        Returns:
            bytes: Binary representation of this instance.

        """
        self._update_checksum(ip_header)
        return super().pack(value)

    def unpack(self, buff:bytes, offset=0):
        """Unpack a binary struct into this object's attributes.

        Return the values instead of the lib's basic types.

        Args:
            buff (bytes): Binary buffer.
            offset (int): Where to begin unpacking.

        Raises:
            :exc:`~.exceptions.UnpackException`: If unpack fails.

        """
        super().unpack(buff, offset)
        self.src_port = self.src_port.value
        self.dst_port = self.dst_port.value
        self.length = self.length.value
        self.checksum = self.checksum.value
        self.data = self.data.value
