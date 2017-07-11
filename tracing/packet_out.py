""" This module was created to remove OpenFlow-specific actions from
the main TraceManager module.
"""

from kytos.core import KytosEvent, log
from pyof.v0x01.common.action import ActionOutput
from pyof.v0x01.controller2switch.packet_out import PacketOut
from napps.amlight.sdntrace import settings


def send_packet_out(controller, switch, port, data):
    """ Just prepare and send a PacketOut used by
    the Tracer. """
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
