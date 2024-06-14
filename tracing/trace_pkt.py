"""
    This module has functions used to pack and unpack the Ethernet frame
     used by PacketOuts and PacketIns.
"""


import dill
from pyof.foundation.network_types import Ethernet, IPv4, VLAN
from napps.amlight.sdntrace import constants
from napps.amlight.sdntrace.tracing.trace_msg import TraceMsg
from napps.amlight.sdntrace.shared.extd_nw_types import TCP, UDP
from napps.amlight.sdntrace.shared.switches import Switches
from napps.amlight.sdntrace.shared.colors import Colors


def generate_trace_pkt(trace_entries, color, r_id):
    """ Receives the REST/PUT to generate a PacketOut
    data needs to be serialized. The goal is always to create
    a packet with data being the TraceMsg to differentiate different
    traces running in parallel. We will stack layers depending of
    the user request. If user submits just a VLAN ID, we will use
    ethertype 88b5 and add TraceMsg after it. Same for IP, however
    the protocol will be 65535. If user provides all the way to TCP/UDP
    we will add TraceMsg after it. First thing is to discover
    what it is that the user has provided.

    Args:
        trace_entries: TraceEntries provided by user or collected from PacketIn
        color: result from Coloring Napp for a specific DPID
        r_id: request ID

    Returns:
        in_port: in_port
        pkt: serialized Ethernet frame
    """

    ethernet = _create_ethernet_frame(trace_entries, color)

    msg = TraceMsg(r_id)

    if ethernet.ether_type == constants.IPV4:
        ip_pkt = _create_ip_packet(trace_entries)
        if ip_pkt.protocol == constants.TCP:
            tp_pkt = _create_tcp_packet(trace_entries)
            tp_pkt.data = dill.dumps(msg)
            ip_pkt.data = tp_pkt.pack(ip_pkt)
        elif ip_pkt.protocol == constants.UDP:
            udp_pkt = _create_udp_packet(trace_entries)
            udp_pkt.data = dill.dumps(msg)
            ip_pkt.data = udp_pkt.pack(ip_pkt)
        else:
            ip_pkt.data = dill.dumps(msg)

        ethernet.data = ip_pkt.pack()
    else:
        ethernet.data = dill.dumps(msg)

    pkt = ethernet.pack()
    return trace_entries.in_port, pkt


def prepare_next_packet(trace_entries, result, event):
    """ Used to support VLAN translation. Currently, it does not
    support translation of other fields, such as MAC addresses.

    Args:
        trace_entries: TraceEntries provided by user or collected from PacketIn
        result: Result of the last Trace Probe sent.
        event: PacketIn event

    Returns:
        trace_entries: TraceEntries customized with new VLAN
        color: result from Coloring Napp for a specific DPID
        switch: DPID
    """
    dpid = result['dpid']
    switch, color = _get_node_color_from_dpid(dpid)

    trace_entries.dpid = dpid

    if event.content['message'].header.version == 1:
        in_port = event.content['message'].in_port.value
        trace_entries.in_port = in_port
    else:
        in_port = event.message.in_port
        trace_entries.in_port = in_port

    vlan = _get_vlan_from_pkt(event.content['message'].data.value)
    if vlan:
        trace_entries.dl_vlan = vlan
    return trace_entries, color, switch


def process_packet(ethernet):
    """Navigates through the Ethernet payload looking for the
    TraceMsg(). TraceMsg is the payload after all protocols of
    the TCP/IP stack.

    Args:
        ethernet: ethernet frame

    Returns:
        TraceMsg in the binary format
    """
    offset = 0

    trace_msg = ethernet.data.value

    if ethernet.ether_type == constants.IPV4:
        ip_pkt = IPv4()
        ip_pkt.unpack(ethernet.data.value, offset)
        offset += ip_pkt.length
        trace_msg = ip_pkt.data

        if ip_pkt.protocol == constants.TCP:
            transport = TCP()
            transport.unpack(ip_pkt.data)
            trace_msg = transport.data

        elif ip_pkt.protocol == constants.UDP:
            transport = UDP()
            transport.unpack(ip_pkt.data)
            trace_msg = transport.data

    return trace_msg


def _create_ethernet_frame(trace_entries, color):
    """ Create an Ethernet frame using TraceEntries
    and color (dl_src)

    Args:
        trace_entries: TraceEntries provided by user or collected from PacketIn
        color: field and value that indicate the color
    Returns:
        ethernet frame
    """
    ethernet = Ethernet()
    ethernet.ether_type = trace_entries.dl_type

    ethernet.source = color['color_value']
    ethernet.destination = trace_entries.dl_dst

    if trace_entries.dl_vlan:
        vlan = VLAN(vid=trace_entries.dl_vlan,
                    pcp=trace_entries.dl_vlan_pcp)
        ethernet.vlans.append(vlan)
    return ethernet


def _create_ip_packet(trace_entries) -> IPv4:
    """ Create an IP packet using TraceEntries

    Args:
        trace_entries: TraceEntries provided by user or collected from PacketIn
    Returns:
        ip packet
    """
    ip_pkt = IPv4()
    ip_pkt.destination = trace_entries.nw_dst
    ip_pkt.source = trace_entries.nw_src
    ip_pkt.dscp = trace_entries.nw_tos
    ip_pkt.protocol = trace_entries.nw_proto
    return ip_pkt


def _create_tcp_packet(trace_entries) -> TCP:
    """ Create a TCP packet using TraceEntries (FUTURE)

    Args:
        trace_entries: TraceEntries provided by user or collected from PacketIn
    Returns:
        tcp packet
    """
    tcp_pkt = TCP()
    tcp_pkt.src_port = trace_entries.tp_src
    tcp_pkt.dst_port = trace_entries.tp_dst
    return tcp_pkt


def _create_udp_packet(trace_entries) -> UDP:
    """ Create an UDP datagram using TraceEntries (FUTURE)

    Args:
        trace_entries: TraceEntries provided by user or collected from PacketIn
    Returns:
        tcp message
    """
    udp_pkt = UDP()
    udp_pkt.src_port = trace_entries.tp_src
    udp_pkt.dst_port = trace_entries.tp_dst
    return udp_pkt


def _get_node_color_from_dpid(dpid):
    """ Get node color from Coloring Napp

    Args:
        dpid: switch DPID
    Returns:
        switch and color
        0 for not Found
    """
    for switch in Switches().get_switches():
        if dpid == switch.dpid:
            return switch, Colors().get_switch_color(switch.dpid)
    return 0, 0


def _get_vlan_from_pkt(data):
    """ Get VLAN ID from frame. Used for VLAN Translation

    Args:
        data: Ethernet Frame
    Returns:
        VLAN VID
    """
    ethernet = Ethernet()
    ethernet.unpack(data)
    vlans = ethernet.vlans
    if vlans:
        return vlans[0].vid
    return None
