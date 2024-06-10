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
    """TCP - Being developed """

    source_p = UBInt16()
    destination_p = UBInt16()
    sequence_n = UBInt32()
    acknowledgment_n = UBInt32()
    _length_flags = UBInt16()
    window = UBInt16()
    checksum = UBInt16()
    urgent_pointer = UBInt16()
    options = BinaryData()
    data = BinaryData()

    def __init__(self, source_p:int=0, destination_p:int=0, sequence_n:int=0, acknowledgment_n:int=0, h_length:int=5,
                 flags:int=2, window:int=0, checksum:int=0, urgent_pointer:int=0, options:bytes=b'', data:bytes=b''):
        """
        These default values are considering this TCP message is first sent, initiating
         handshake.

        Args:
            source_p(int): Source port. Defaults to 0
            destination_p(int): Destination port. Defaults to 0
            sequence_n(int): Sequence number (raw). Random number [0, 4294967296]
            acknowledgment_n(int): Acknowledgment number (raw). Defaults to 0
            h_length(int): Header length, data offset. Defaults(minimun) to 5 words
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
            window(int): Window. Defaults to 43690
            checksum(int): Checksum. Defaults to 0
            urgent_pointer(int): Urgent pointer. Defaults to 0
            options(bytes): Options. Defaults to empty bytes
            data(bytes): Data. Defaults to empty bytes
        """
        super().__init__()
        self.source_p = source_p
        self.destination_p = destination_p
        self.sequence_n = sequence_n if sequence_n != 0 else randrange(4294967296)
        self.acknowledgment_n = acknowledgment_n
        self.h_length = h_length
        self.flags = flags
        # window default value (b'\xaa\xaa') is an arbitrary number until advised otherwise.
        self.window = window
        self.checksum = checksum
        self.urgent_pointer = urgent_pointer
        self.options = options
        self.data = data

    def _value_by_half_word(self, value: bytes) -> int:
        """Calculate the integer value of the argument partitioned by 2 bytes."""
        total = 0
        while value:
            total = total + int.from_bytes(value[-2:])
            value = value[:-2]
        return total

    def _update_checksum(self, ip_header: Union[IPv4, IPv6]):
        """Update the packet checksum to enable integrity check.
         Each addend is 16 bits."""
        # TODO: Overflown data in practice (91 bytes).
        #       Lenght currently is not accurate
        # self.h_length = 5 + (len(self.options) // 4) + (len(self.data) // 4)
        self.h_length = 5 + (len(self.options) // 4) + 0
        self._length_flags = self.h_length << 12 | self.flags

        sequence_hex = hex(self.sequence_n)[2:]
        acknowledgment_hex = hex(self.acknowledgment_n)[2:]
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
                        destination_lower + ip_header.protocol + (self.h_length * 4))
        else:
            # TODO: Implement IPv6 header analysis
            ip_value = 0

        block_sum = (self.source_p + self.destination_p + sequence_upper +
                         sequence_lower + acknowledgment_upper + acknowledgment_lower +
                         self._length_flags + self.window + 0 + self.urgent_pointer +
                         self._value_by_half_word(self.options) +
                         self._value_by_half_word(self.data) + ip_value)
        
        while block_sum > 65535:
            carry = block_sum >> 16
            block_sum = (block_sum & 65535) + carry

        self.checksum = ~block_sum & 65535

    def pack(self, ip_header: Union[IPv4, IPv6], value=None):
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
        self.source_p = self.source_p.value
        self.destination_p = self.destination_p.value
        self.sequence_n = self.sequence_n.value
        self.acknowledgment_n = self.acknowledgment_n.value
        self.h_length = self._length_flags.value >> 12
        self.flags = self._length_flags.value & 4095
        self.window = self.window.value
        self.checksum = self.checksum.value

        if self.h_length > 5:
            option_size = (self.h_length - 5) * 4
            self.data = self.options.value[option_size:]
            self.options = self.options.value[:option_size]
        else:
            self.data = self.options.value
            self.options = b''


class UDP(GenericStruct):
    """ UDP - Being developed """

    source_p = UBInt16()
    destination_p = UBInt16()
    length = UBInt16()
    checksum = UBInt16()
    data = BinaryData()
    
    def __init__(self, source_p:int=0, destination_p:int=0, length:int=0, checksum:int=0, data:bytes=b''):
        """Create an UDP header with default values.

        Args:
            source_p(int): Source port. Defaults to 0
            destination_p(int): Destination port. Defaults to 0
            length(int): Length. Defaults to 8 (minimum in bytes)
            checksum(int): Checksum. Defaults to 0
            data(bytes): Data. Defults to empty bytes

        """
        self.source_p = source_p
        self.destination_p = destination_p
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

    def _update_checksum(self, ip_header:Union[IPv4, IPv6]):
        """Update the packet checksum to enable integrity check.
         Each addend is 16 bits."""
        # TODO: Length does not include data length
        # self.length = 8 + len(self.data)
        self.length = 8 + 0

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

        block_sum = ip_value + self.source_p + self.destination_p + self.length + self._value_by_16_bits(self.data)

        while block_sum > 65535:
            carry = block_sum >> 16
            block_sum = (block_sum & 65535) + carry

        self.checksum = ~block_sum & 65535

    def pack(self, ip_header:Union[IPv4, IPv6], value=None):
        """Pack the struct in a binary representation.

        Merge some fields to ensure correct packing.

        Returns:
            bytes: Binary representation of this instance.

        """
        self._update_checksum(ip_header)
        return super().pack(value)

    def unpack(self, buff, offset=0):
        """Unpack a binary struct into this object's attributes.

        Return the values instead of the lib's basic types.

        Args:
            buff (bytes): Binary buffer.
            offset (int): Where to begin unpacking.

        Raises:
            :exc:`~.exceptions.UnpackException`: If unpack fails.

        """
        super().unpack(buff, offset)
        self.source_p = self.source_p.value
        self.destination_p = self.destination_p.value
        self.length = self.length.value
        self.checksum = self.checksum.value
        self.data = self.data.value
