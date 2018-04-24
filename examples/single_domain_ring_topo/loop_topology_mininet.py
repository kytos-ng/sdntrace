#!/usr/bin/python

"""
This example creates a single-controller network in a loop topology by
using the net.add*() API and manually starting the switches and controllers.
"""

from mininet.clean import Cleanup
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel


ip = '192.168.56.1'


def int2dpid(dpid):
    """

    :param dpid:
    :return:
    """
    try:
        dpid = hex(dpid)[2:]
        dpid = '0' * (16 - len(dpid)) + dpid
        return dpid
    except IndexError:
        raise Exception('Unable to derive default datapath ID - '
                        'please either specify a dpid or use a '
                        'canonical switch name such as s23.')


def single_domain():
    """Create a network from semi-scratch with multiple controllers."""
    net = Mininet(topo=None, build=False)

    # Add switches
    s1 = net.addSwitch('s1', listenPort=6601, dpid=int2dpid(1))
    s2 = net.addSwitch('s2', listenPort=6602, dpid=int2dpid(2))
    s3 = net.addSwitch('s3', listenPort=6603, dpid=int2dpid(3))
    s4 = net.addSwitch('s4', listenPort=6604, dpid=int2dpid(4))
    s5 = net.addSwitch('s5', listenPort=6605, dpid=int2dpid(5))

    # Add links
    net.addLink(s1, s2, port1=2, port2=2)
    net.addLink(s2, s3, port1=3, port2=3)
    net.addLink(s3, s4, port1=4, port2=4)
    net.addLink(s4, s5, port1=5, port2=5)
    net.addLink(s5, s1, port1=6, port2=6)
    net.addLink(s1, s3, port1=7, port2=7)

    # Add hosts
    h1 = net.addHost('h1', mac='dd:00:00:00:00:11')
    h2 = net.addHost('h2', mac='dd:00:00:00:00:22')
    h3 = net.addHost('h3', mac='dd:00:00:00:00:33')
    h4 = net.addHost('h4', mac='dd:00:00:00:00:44')
    h5 = net.addHost('h5', mac='dd:00:00:00:00:55')

    # Add links to switches
    net.addLink(s1, h1, port1=1, port2=1)
    net.addLink(s2, h2, port1=1, port2=1)
    net.addLink(s3, h3, port1=1, port2=1)
    net.addLink(s4, h4, port1=1, port2=1)
    net.addLink(s5, h5, port1=1, port2=1)

    net.addController('ctrl', controller=RemoteController, ip=ip, port=6633)

    net.build()
    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')  # for CLI output
    Cleanup.cleanup()
    single_domain()
