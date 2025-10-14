"""
    Module to transparently process OpenFlow requests,
"""


import napps.amlight.sdntrace.backends.openflow13 as openflow13
from kytos.core import log


def process_packet_in(event):
    """

    Args:
        event
    Return:
        ethernet: frame
        in_port: incoming port
        switch: incoming switch
    """
    of_version = event.content['message'].header.version
    if of_version.value == 4:
        return openflow13.packet_in(event, event.content['message'])

    log.error("Invalid OpenFlow version")
    return 0, 0, 0

async def send_packet_out(controller, switch, port, data):
    """ Just prepare and send a PacketOut used by
    the Tracer.

    Args:
        controller: Kytos controller
        switch: OpenFlow datapath
        port: in_port
        data: Ethernet frame
    """

    of_version = switch.features.header.version

    if of_version.value == 4:
        await openflow13.send_packet_out(controller, switch, port, data)
    else:
        log.error("Invalid OpenFlow version")
        return
