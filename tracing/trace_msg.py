""" This module creates the TraceID message to be used as the
Ethernet payload of the PacketOut. This msg is important to
differentiate parallel traces.
"""


class TraceMsg(object):
    """ This class will be used to create, retrieve and update the
    payload message sent through the trace process

    Basically the msg is a dictionary:

    {"trace": {
            "request_id": "number to identify this trace"
        }
    }
    """

    def __init__(self, r_id='0', step=0):
        self._request_id = None
        self._step = None
        self._instantiate_vars(r_id, step)

    def _instantiate_vars(self, r_id, step):
        """ Attributes in the TraceMsg are processed as
        Getter and Setters.

        Args:
            r_id: request ID
        """
        self.request_id = r_id
        self.step = step

    @property
    def request_id(self):
        """ Getter: Request ID """
        return self._request_id

    @request_id.setter
    def request_id(self, r_id):
        """ Setter: Request ID """
        try:
            if isinstance(r_id, int):
                self._request_id = r_id
            else:
                self._request_id = int(r_id)
        except ValueError:
            raise ValueError("Invalid ID provided: %s" % r_id)

    @property
    def step(self):
        """ Getter: Step number """
        return self._step

    @step.setter
    def step(self, step):
        """ Setter: Step number """
        try:
            if isinstance(step, int):
                self._step = step
            else:
                self._step = int(step)
        except ValueError:
            raise ValueError(f"Invalid step number provided: f{step}")
