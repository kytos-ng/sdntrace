#!/usr/bin/env bash

SWITCHES="s1 s2 s3 s4 s5"

if [ ! -z $1  ]; then
    PROTO="OpenFlow10"
else
    PROTO="OpenFlow13"
fi

for sw in $SWITCHES; do
    ovs-vsctl set Bridge $sw protocols=$PROTO
    ovs-ofctl del-flows $sw -O $PROTO
    ovs-vsctl set Bridge $sw other-config:dp-desc=$sw
done

ovs-ofctl del-flows s1 -O $PROTO
ovs-ofctl del-flows s2 -O $PROTO
ovs-ofctl del-flows s3 -O $PROTO
ovs-ofctl del-flows s4 -O $PROTO
ovs-ofctl del-flows s5 -O $PROTO

ovs-ofctl add-flow s1 "priority=1 actions=drop" -O $PROTO
ovs-ofctl add-flow s2 "priority=1 actions=drop" -O $PROTO
ovs-ofctl add-flow s3 "priority=1 actions=drop" -O $PROTO
ovs-ofctl add-flow s4 "priority=1 actions=drop" -O $PROTO
ovs-ofctl add-flow s5 "priority=1 actions=drop" -O $PROTO

# From h1 to h4 - ok
ovs-ofctl add-flow s1 "in_port=1 actions=mod_vlan_vid:200,output:2" -O $PROTO
ovs-ofctl add-flow s2 "in_port=2,dl_vlan=200 actions=output:3" -O $PROTO
ovs-ofctl add-flow s3 "in_port=3,dl_vlan=200 actions=output:4" -O $PROTO
ovs-ofctl add-flow s4 "in_port=4,dl_vlan=200 actions=strip_vlan,output:1" -O $PROTO

#From h4 to h1 - ok
ovs-ofctl add-flow s4 "in_port=1 actions=mod_vlan_vid:200,output:4" -O $PROTO
ovs-ofctl add-flow s3 "in_port=4,dl_vlan=200 actions=output:3" -O $PROTO
ovs-ofctl add-flow s2 "in_port=3,dl_vlan=200 actions=output:2" -O $PROTO
ovs-ofctl add-flow s1 "in_port=2,dl_vlan=200 actions=strip_vlan,output:1" -O $PROTO
