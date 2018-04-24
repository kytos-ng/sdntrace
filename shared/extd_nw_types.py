"""Extends Network packet types.

Defines and Implements Basic Network packet types, such as VLAN, TCP and UDP.

TODO: Complete it
"""

from pyof.foundation.base import GenericStruct
from pyof.foundation.basic_types import (BinaryData, UBInt16)


__all__ = ('TCP', 'UDP')


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
