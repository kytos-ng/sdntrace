"""
    Class Entries. Used to evaluate entries provided.
"""
import re


DPID_ADDR = re.compile('([0-9A-Fa-f]{2}[-:]){7}[0-9A-Fa-f]{2}$')
MAC_ADDR = re.compile('([0-9A-Fa-f]{2}[-:]){5}[0-9A-Fa-f]{2}$')
IP_ADDR = re.compile("^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}"
                     "(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")


class TraceEntries(object):
    """ Class Entries. Used to evaluate entries provided. """

    def __init__(self):
        self._dpid = 0
        self._in_port = 0
        self._dl_src = 0
        self._dl_dst = 'ca:fe:ca:fe:ca:fe'
        self._dl_vlan = 0
        self._dl_type = 0x800
        self._dl_vlan_pcp = 0
        self._nw_src = '1.1.1.1'
        self._nw_dst = '1.1.1.2'
        self._nw_tos = 0
        self._nw_proto = 0
        self._tp_src = 0
        self._tp_dst = 0
        self.init_entries = dict()  # User request

    @property
    def dpid(self):
        """ Property dpid """
        return self._dpid

    @dpid.setter
    def dpid(self, dpid):
        """ Validates DPID formats: '1', 'a',  '0000000000000001',
        'abcdefabcdefabcd', 'ab:cd:ef:ab:cd:ef:ab:cd'

        Args:
            dpid: entries['trace']['switch']['dpid']
        """
        if not isinstance(dpid, str):
            raise ValueError("Error: dpid has to be string")

        if 0 < len(dpid) <= 16:  # pylint: disable=len-as-condition
            # DPIDs: '1', 'a', '0000000000000001', 'abcdefabcdefabcd'
            if dpid.isalnum():
                if not re.search('[g-z]', dpid.lower()):
                    error_len = False
                else:
                    error_len = True
            else:
                error_len = True

        elif len(dpid) == 23:
            # DPIDs: 'ab:cd:ef:ab:cd:ef:ab:cd'
            # Valid chars: 0-9, :, a-f, A-Z
            if re.search(DPID_ADDR, dpid):
                error_len = False
            else:
                error_len = True
        else:
            error_len = True

        if error_len:
            msg = "Error: dpid allows [a-f], int, and :. Lengths: 1-16 and 23"
            raise ValueError(msg)

        self._dpid = dpid

    @property
    def in_port(self):
        """ IN_PORT Getter """
        return self._in_port

    @in_port.setter
    def in_port(self, in_port):
        """ IN_PORT Setter """
        if not isinstance(in_port, int):
            raise ValueError("Error: in_port has to be integer")
        else:
            if in_port <= 0 or in_port >= 2**64:
                raise ValueError("Error: in_port has to be > 0")

        self._in_port = in_port

    @property
    def dl_src(self):
        """ dl_src Getter """
        return self._dl_src

    @dl_src.setter
    def dl_src(self, dl_src):
        """ dl_src Setter: entries['trace']['eth']['dl_src'].
        Validates MAC formats: 'ab:cd:ef:ab:cd:ef'

        Args:
            dl_src: entries['trace']['eth']['dl_src']
        """

        if not isinstance(dl_src, str):
            raise ValueError("Error: dl_src has to be string")

        elif not re.search(MAC_ADDR, dl_src):
            # DPIDs: 'ab:cd:ef:ab:cd:ef'
            # Valid chars: 0-9, :, a-f, A-Z
            msg = "Error: dl_src allows char [a-f], int, and :. Lengths: 17"
            raise ValueError(msg)

        self._dl_src = dl_src

    @property
    def dl_dst(self):
        """ dl_dst Getter """
        return self._dl_dst

    @dl_dst.setter
    def dl_dst(self, dl_dst):
        """ dl_dst Setter: entries['trace']['eth']['dl_dst'].
        Validates MAC formats: 'ab:cd:ef:ab:cd:ef'

        Args:
            dl_dst: entries['trace']['eth']['dl_dst']
        """

        if not isinstance(dl_dst, str):
            raise ValueError("Error: dl_dst has to be string")

        elif not re.search(MAC_ADDR, dl_dst):
            # DPIDs: 'ab:cd:ef:ab:cd:ef'
            # Valid chars: 0-9, :, a-f, A-Z
            msg = "Error: dl_dst allows char [a-f], int, and :. Lengths: 17"
            raise ValueError(msg)

        self._dl_dst = dl_dst

    @property
    def dl_vlan(self):
        """ dl_vlan Getter """
        return self._dl_vlan

    @dl_vlan.setter
    def dl_vlan(self, dl_vlan):
        """ dl_vlan Setter """
        if not isinstance(dl_vlan, int):
            raise ValueError("Error: dl_vlan has to be integer")
        else:
            if not 0 < dl_vlan <= 4095:
                raise ValueError("Error: dl_vlan has to be between 0 and 4095")

        self._dl_vlan = dl_vlan

    @property
    def dl_type(self):
        """ dl_type Getter """
        return self._dl_type

    @dl_type.setter
    def dl_type(self, dl_type):
        """ dl_type Setter """
        if not isinstance(dl_type, int):
            raise ValueError("Error: dl_type has to be integer")
        else:
            if not 0 < dl_type <= 65535:
                raise ValueError("Error: dl_type has to be [0-65535]")

        self._dl_type = dl_type

    @property
    def dl_vlan_pcp(self):
        """ dl_vlan_pcp Getter """
        return self._dl_vlan_pcp

    @dl_vlan_pcp.setter
    def dl_vlan_pcp(self, dl_vlan_pcp):
        """ dl_vlan_pcp Setter """
        if not isinstance(dl_vlan_pcp, int):
            raise ValueError("Error: dl_vlan_pcp has to be integer")
        else:
            if not 0 < dl_vlan_pcp <= 7:
                raise ValueError("Error: dl_vlan_pcp has to be [0-7]")

        self._dl_vlan_pcp = dl_vlan_pcp

    @property
    def nw_tos(self):
        """ nw_tos Getter """
        return self._nw_tos

    @nw_tos.setter
    def nw_tos(self, nw_tos):
        """ nw_tos Setter """
        if not isinstance(nw_tos, int):
            raise ValueError("Error: nw_tos has to be integer")
        else:
            if not 0 < nw_tos <= 7:
                raise ValueError("Error: nw_tos has to be between 0 and 7")

        self._nw_tos = nw_tos

    @property
    def nw_src(self):
        """ nw_src Getter """
        return self._nw_src

    @nw_src.setter
    def nw_src(self, nw_src):
        """ nw_src Setter """

        if not isinstance(nw_src, str):
            raise ValueError("Error: nw_src has to be string")

        elif not re.search(IP_ADDR, nw_src):
            # Filters: 0.0.0.1 to 255.255.255.255
            msg = "Error: nw_src is not a proper IPv4"
            raise ValueError(msg)

        self._nw_src = nw_src

    @property
    def nw_dst(self):
        """ nw_dst Getter """
        return self._nw_dst

    @nw_dst.setter
    def nw_dst(self, nw_dst):
        """ nw_dst Setter """

        if not isinstance(nw_dst, str):
            raise ValueError("Error: nw_dst has to be string")

        elif not re.search(IP_ADDR, nw_dst):
            # Filters: 0.0.0.1 to 255.255.255.255
            msg = "Error: nw_dst is not a proper IPv4"
            raise ValueError(msg)

        self._nw_dst = nw_dst

    @property
    def nw_proto(self):
        """ nw_proto Getter """
        return self._nw_proto

    @nw_proto.setter
    def nw_proto(self, nw_proto):
        """ nw_proto Setter """
        if not isinstance(nw_proto, int):
            raise ValueError("Error: nw_proto has to be integer")
        else:
            if not 0 < nw_proto <= 65535:
                raise ValueError("Error: nw_proto has to be [0-65535]")

        self._nw_proto = nw_proto

    @property
    def tp_src(self):
        """ tp_src Getter """
        return self._tp_src

    @tp_src.setter
    def tp_src(self, tp_src):
        """ tp_src Setter """
        if not isinstance(tp_src, int):
            raise ValueError("Error: tp_src has to be integer")
        else:
            if not 0 < tp_src <= 65535:
                raise ValueError("Error: tp_src has to be between 0 and 65535")

        self._tp_src = tp_src

    @property
    def tp_dst(self):
        """ tp_dst Getter """
        return self._tp_dst

    @tp_dst.setter
    def tp_dst(self, tp_dst):
        """ tp_dst Setter """
        if not isinstance(tp_dst, int):
            raise ValueError("Error: tp_dst has to be integer")
        else:
            if not 0 < tp_dst <= 65535:
                raise ValueError("Error: tp_dst has to be between 0 and 65535")

        self._tp_dst = tp_dst

    def load_entries(self, entries):
        """ Import entries provided

        Args:
            entries: user-provided entries
        """
        # Basic entries['trace']
        if 'trace' not in entries:
            raise ValueError("Error: Trace key entry missing")
        elif not isinstance(entries['trace'], dict):
            raise ValueError("Error: Trace has to be dict")

        trace = entries['trace']

        # Basic entries['trace']['switch']
        if 'switch' not in trace:
            raise ValueError("Error: switch key not provided")
        elif not isinstance(trace['switch'], dict):
            raise ValueError("Error: switch has to be dict")

        switch = trace['switch']

        if 'dpid' not in switch:
            raise ValueError("Error: dpid not provided")
        else:
            self.dpid = switch['dpid']

        if 'in_port' not in switch:
            raise ValueError("Error: in_port not provided")
        else:
            self.in_port = switch['in_port']

        # Basic entries['trace']['switch']
        eth = trace.get("eth", {})
        if not isinstance(eth, dict):
            raise ValueError("Error: eth has to be dict")

        if 'dl_vlan' in eth:
            self.dl_vlan = eth['dl_vlan']

        if 'dl_src' in eth:
            self.dl_src = eth['dl_src']

        if 'dl_dst' in eth:
            self.dl_dst = eth['dl_dst']

        if 'dl_vlan_pcp' in eth:
            self.dl_vlan_pcp = eth['dl_vlan_pcp']

        if 'dl_type' in eth:
            self.dl_type = eth['dl_type']

        # Basic entries['trace']['ip']
        if 'ip' in trace:
            ip_ = trace['ip']

            if 'nw_src' in ip_:
                self.nw_src = ip_['nw_src']

            if 'nw_dst' in ip_:
                self.nw_dst = ip_['nw_dst']

            if 'nw_tos' in ip_:
                self.nw_tos = ip_['nw_tos']

            if 'nw_proto' in ip_:
                self.nw_proto = ip_['nw_proto']
                if 'tp' not in trace:
                    raise ValueError("Error: tp not provided")

        # Basic entries['trace']['ip']
        if 'tp' in trace:
            tp_ = trace['tp']

            if 'tp_src' in tp_:
                self.tp_src = tp_['tp_src']

            if 'tp_dst' in tp_:
                self.tp_dst = tp_['tp_dst']

        self.init_entries = entries
