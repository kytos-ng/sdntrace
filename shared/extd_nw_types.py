"""Extends Network packet types.

Defines and Implements Basic Network packet types, such as VLAN, TCP and UDP.
"""

from pyof.foundation.base import GenericStruct
from pyof.foundation.basic_types import (BinaryData, UBInt16)


__all__ = ('VLAN', 'TCP', 'UDP')


class VLAN(GenericStruct):
    """VLAN

    """

    #: _prio_cfi_id: (:class:`UBInt16`): Priority, CFI and VID
    _prio_cfi_id = UBInt16()
    #: ether_type (:class:`UBInt16`): The EtherType of the packet.
    ether_type = UBInt16()

    #: data (:class:`BinaryData`): The content of the packet in binary format.
    data = BinaryData()

    def __init__(self, vid=0, pcp=0, cfi=0, ether_type=0, data=b''):
        super().__init__()
        self.ether_type = ether_type
        self.pcp = pcp  # Default 0 means Best Effort queue
        self.cfi = cfi  # Default is 0 for Ethernet
        self.vid = vid

        self.data = data
        self._prio_cfi_id = 1

    def pack(self, value=None):
        """Pack the struct in a binary representation.

        Merge some fields to ensure correct packing.
        """
        self._prio_cfi_id = self.pcp << 13 | self.cfi << 12 | self.vid
        return super().pack()

    def unpack(self, buffer, offset=0):
        """Unpack a binary message into this object's attributes.

        Unpack the binary value *buff* and update this object attributes based
        on the results.

        Args:
            buffer (bytes): Binary data package to be unpacked.
            offset (int): Where to begin unpacking.

        Raises:
            Exception: If there is a struct unpacking error.
        """
        prio_cfi_id = UBInt16()
        prio_cfi_id.unpack(buffer[offset:2])

        self.pcp = prio_cfi_id.value >> 13
        self.cfi = (prio_cfi_id.value & 0x1000) >> 12
        self.vid = prio_cfi_id.value & 0xfff

        etype = UBInt16()
        etype.unpack(buffer[offset+2:4])
        self.ether_type = etype.value


class TCP(GenericStruct):
    """TCP

    """

    #: data (:class:`BinaryData`): The content of the packet in binary format.
    data = BinaryData()

    def __init__(self):
        super().__init__()

    def pack(self, value=None):
        """Pack the struct in a binary representation.
        Merge some fields to ensure correct packing.

        Args:
            value:
        """
        return super().pack()

    def unpack(self, buffer, offset=0):
        """Unpack a binary message into this object's attributes.

        Unpack the binary value *buff* and update this object attributes based
        on the results.

        Args:
            buffer (bytes): Binary data package to be unpacked.
            offset (int): Where to begin unpacking.

        Raises:
            Exception: If there is a struct unpacking error.
        """
        pass


class UDP(GenericStruct):
    """TCP

    """

    #: data (:class:`BinaryData`): The content of the packet in binary format.
    data = BinaryData()

    def __init__(self):
        super().__init__()

    def pack(self, value=None):
        """Pack the struct in a binary representation.
        Merge some fields to ensure correct packing.

        Args:
            value:
        """
        return super().pack()

    def unpack(self, buffer, offset=0):
        """Unpack a binary message into this object's attributes.

        Unpack the binary value *buff* and update this object attributes based
        on the results.

        Args:
            buffer (bytes): Binary data package to be unpacked.
            offset (int): Where to begin unpacking.

        Raises:
            Exception: If there is a struct unpacking error.
        """
        pass
