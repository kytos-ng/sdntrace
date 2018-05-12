"""
    Module to transparently process OpenFlow requests,
"""


from kytos.core import log
import napps.amlight.sdntrace.backends.openflow10 as openflow10
import napps.amlight.sdntrace.backends.openflow13 as openflow13


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
    if of_version.value == 1:
        return openflow10.packet_in(event, event.content['message'])
    elif of_version.value == 4:
        return openflow13.packet_in(event, event.content['message'])

    log.error("Invalid OpenFlow version")
    return 0, 0, 0


def send_packet_out(controller, switch, port, data):
    """ Just prepare and send a PacketOut used by
    the Tracer.

    Args:
        controller: Kytos controller
        switch: OpenFlow datapath
        port: in_port
        data: Ethernet frame
    """

    of_version = switch.features.header.version

    if of_version.value == 1:
        openflow10.send_packet_out(controller, switch, port, data)
    elif of_version.value == 4:
        openflow13.send_packet_out(controller, switch, port, data)
    else:
        log.error("Invalid OpenFlow version")
        return
