""" This module creates the trace result to be exported via REST.
Each active trace will instantiate a FormatRest and publish it.
"""
from datetime import datetime
from napps.amlight.sdntrace.shared.switches import Switches


class FormatRest:
    """ This module creates the trace result to be exported via REST.
    Each active trace will instantiate a FormatRest and publish it.
    """

    def __init__(self):
        self.start_time = self.current_time()

    @staticmethod
    def current_time():
        """ Return the current time using datetime format"""
        return datetime.now()

    def get_time(self, to_str=True):
        """ Get tracing total trace per trace step.

        Args:
            to_str: if the result should be provided in string
                otherwise, would be datetime format
        Return:
            total time from current time and start time
        """
        time_diff = self.current_time() - self.start_time
        return str(time_diff) if to_str else time_diff

    def add_trace_step(self, trace_result, trace_type, reason='done',
                       dpid=None, port=None, msg="none"):
        """ Used to create the new REST result.vOnly this method
        should write to self.trace_result

        Args:
            trace_result: variable with results
            trace_type: type of trace (intra or inter-domain)
            reason: reason in case trace_type == last
            dpid: switch's dpid
            port: switch's OpenFlow port_no
            msg: message in case of reason == error
        """
        step = dict()
        step["type"] = trace_type

        switch = Switches().get_switch(dpid) if dpid else None

        if trace_type == 'starting':
            step["dpid"] = switch.dpid
            step["port"] = port
            step["time"] = str(self.start_time)
        elif trace_type == 'trace':
            step["dpid"] = switch.dpid
            step["port"] = port
            step["time"] = self.get_time()
        elif trace_type == 'last':
            step["reason"] = reason
            step["msg"] = msg
            step["time"] = self.get_time()

        # Add to trace_result array by reference
        trace_result.append(step)
