"""
    Module to process OpenFlow 1.0 packet manipulation
"""


from pyof.v0x01.common.action import ActionOutput
from pyof.v0x01.controller2switch.packet_out import PacketOut
from pyof.foundation.network_types import Ethernet
from kytos.core import KytosEvent, log
from napps.amlight.sdntrace import settings


def packet_in(event, packet_in):
    """ Process OpenFlow 1.0 PacketIn messages

    Args:
        event: PacketIN event
        packet_in: PacketIn msg
    Return:
        ethernet: PacketIn data
        in_port: in_port
        switch: OpenFlow datapath
        0, 0, 0 if it is not a trace probe
    """

    ethernet = Ethernet()
    ethernet.unpack(packet_in.data.value)

    if settings.COLOR_VALUE in ethernet.source.value:
        log.debug("OpenFlow 1.0 PacketIn Trace Msg Received")

        in_port = packet_in.in_port.value
        switch = event.source.switch
        return ethernet, in_port, switch

    log.debug("PacketIn is not a Data Trace Probe")
    return 0, 0, 0


def send_packet_out(controller, switch, port, data):
    """ Just prepare the PacketOut to be used by the Tracer.

    Args:
        controller: Kytos controller
        switch: OpenFlow datapath
        port: in_port
        data: Ethernet frame
    Return:
        output_action = ActionOutput
    """
    output_action = ActionOutput()
    output_action.port = settings.OFPP_TABLE

    packet_out = PacketOut()
    packet_out.actions.append(output_action)
    packet_out.in_port = port
    packet_out.data = bytes(data)

    event_out = KytosEvent()
    event_out.name = 'kytos/of_lldp.messages.out.ofpt_packet_out'
    event_out.content = {'destination': switch.connection,
                         'message': packet_out}

    log.debug('PacketOut %s sent' % event_out.content)
    controller.buffers.msg_out.put(event_out)
