"""
    This module has functions used to create the Ethernet frame
     used by PacketOuts and PacketIns.
"""

import dill
from pyof.foundation.network_types import Ethernet, IPv4, VLAN
from napps.amlight.sdntrace import settings, constants
from napps.amlight.sdntrace.tracing.trace_msg import TraceMsg
from napps.amlight.sdntrace.shared.extd_nw_types import TCP, UDP
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.shared.colors import Colors


def generate_trace_pkt(entries, color, r_id, my_domain):
    """ Receives the REST/PUT to generate a PacketOut
    data needs to be serialized.

    Args:
        entries:
        color: result from Coloring Napp for a specific DPID
        r_id:
        my_domain:

    Returns:
        in_port:
        pkt:
    """

    trace = {}
    switch = {}
    eth = {}
    ip = {}
    tp = {}

    # TODO Validate for dl_vlan. If empty, return error.

    # Default values
    dpid, in_port = 0, 65532
    if color['color_field'] == 'dl_src':
        dl_src = color['color_value']
    else:
        dl_src = '0e:55:05:0e:55:05'
    dl_dst = "ca:fe:ca:fe:ca:fe"
    dl_vlan, dl_type, dl_vlan_pcp = 100, 2048, 0
    nw_src, nw_dst, nw_tos = '127.0.0.1', '127.0.0.1', 0
    tp_src, tp_dst = 1, 1

    try:
        trace = entries['trace']
        switch = trace['switch']
        eth = trace['eth']
    except:
        pass

    try:
        ip = trace['ip']
    except:
        pass

    try:
        tp = trace['tp']
    except:
        pass

    if len(switch) > 0:
        dpid, in_port = prepare_switch(switch, dpid, in_port)

    if len(eth) > 0:
        dl_src, dl_dst, dl_vlan, dl_type, dl_vlan_pcp = prepare_ethernet(eth, dl_src, dl_dst,
                                                                         dl_vlan, dl_type,
                                                                         dl_vlan_pcp)
    # if len(ip) > 0:
    nw_src, nw_dst, nw_tos = prepare_ip(ip, nw_src, nw_dst, nw_tos)

    # if len(tp) > 0:
    tp_src, tp_dst = prepare_tp(tp, tp_src, tp_dst)

    kethernet = Ethernet()
    kethernet.ether_type = int(dl_type)
    kethernet.source = dl_src
    kethernet.destination = dl_dst

    kvlan = VLAN(vid=int(dl_vlan), pcp=dl_vlan_pcp)
    kethernet.vlan = kvlan

    msg = TraceMsg(r_id, my_domain)

    if int(dl_type) == constants.IPv4:

        kip = IPv4()
        kip.destination = nw_dst
        kip.source = nw_src
        # ip.protocol = 6
        kip.data = dill.dumps(msg)
        kethernet.data = kip.pack()
    else:
        kethernet.data = dill.dumps(msg)

    pkt = kethernet.pack()
    return in_port, pkt


def prepare_next_packet(entries, result, ev):
    """ Used to support VLAN translation. Currently, it does not
    support translation of other fields, such as MAC addresses.

    Args:
        entries:
        result:
        ev:

    Returns:
        entries:
        color: result from Coloring Napp for a specific DPID
        switch:
    """
    dpid = result['dpid']
    switch, color = get_node_color_from_dpid(dpid)

    entries['trace']['switch']['dpid'] = dpid

    if ev.content['message'].header.version == 1:
        in_port = ev.content['message'].in_port.value
        entries['trace']['switch']['in_port'] = in_port
    else:
        # TODO: fix it
        in_port = ev.content['message'].match['in_port']
        entries['trace']['switch']['in_port'] = in_port

    entries['trace']['eth']['dl_vlan'] = get_vlan_from_pkt(ev.content['message'].data.value)

    return entries, color, switch


def process_packet(ethernet):
        """Navigates through the Ethernet payload looking for the
        TraceMsg(). TraceMsg is the payload after all protocols of
        the TCP/IP stack.

        Args:
            ethernet: ethernet frame

        Returns:
            TraceMsg in the binary format
        """
        etype = ethernet.ether_type
        offset = 0

        trace_msg = ethernet.data.value

        if etype == constants.IPv4:
            ip = IPv4()
            ip.unpack(ethernet.data.value, offset)
            offset += ip.length
            trace_msg = extract_trace_msg(ip.data)

            if ip.protocol == constants.TCP:
                transport = TCP()
                transport.parse(ethernet.data.value, offset)
                offset += transport.length
                trace_msg = extract_trace_msg(transport.data)

            if ip.protocol == constants.UDP:
                transport = UDP()
                transport.parse(ethernet.data.value, offset)
                offset += transport.length
                trace_msg = extract_trace_msg(transport.data)

        return trace_msg


def extract_trace_msg(data):
    try:
        return data.value
    except:
        return data


def get_node_color_from_dpid(dpid):
    for switch in Switches().get_switches():
        if dpid == switch.dpid:
            return switch, Colors().get_switch_color(switch.dpid)
    return 0


def get_vlan_from_pkt(data):

    ethernet = Ethernet()
    ethernet.unpack(data)

    return ethernet.vlan.vid


def prepare_switch(switch, dpid, in_port):
    for idx in switch:
        if idx == 'dpid':
            dpid = switch[idx]
        elif idx == 'in_port':
            in_port = switch[idx]
    return dpid, in_port


def prepare_ethernet(eth, dl_src, dl_dst, dl_vlan, dl_type, dl_vlan_pcp):
    for idx in eth:
        if idx == 'dl_src':
            dl_src = eth[idx]
        elif idx == 'dl_dst':
            dl_dst = eth[idx]
        elif idx == 'dl_vlan':
            dl_vlan = eth[idx]
        elif idx == 'dl_type':
            dl_type = eth[idx]
        elif idx == 'dl_vlan_pcp':
            dl_vlan_pcp = eth[idx]
    return dl_src, dl_dst, dl_vlan, dl_type, dl_vlan_pcp


def prepare_ip(ip, nw_src, nw_dst, nw_tos):
    for idx in ip:
        if idx == 'nw_src':
            nw_src = ip[idx]
        elif idx == 'nw_dst':
            nw_dst = ip[idx]
        elif idx == 'nw_tos':
            nw_tos = ip[idx]
    return nw_src, nw_dst, nw_tos


def prepare_tp(tp, tp_src, tp_dst):
    for idx in tp:
        if idx == 'tp_src':
            tp_src = tp[idx]
        elif idx == 'tp_dst':
            tp_dst = tp[idx]
    return tp_src, tp_dst
