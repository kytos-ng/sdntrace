"""
    Module to interact with Coloring Napp.
"""


import requests
import json
from kytos.core import log


class Colors(object):

    def __init__(self):
        """ Instantiate Colors and get list of colors
        """
        self._url = 'http://localhost:8181/kytos/coloring/colors'
        self._colors = dict()
        self._get_colors()

    def _get_colors(self):
        """ Get list of colors
        """
        try:
            result = requests.get(url=self._url)
            if result.status_code == 200:
                result = json.loads(result.content)
                self._colors = result['colors']
            else:
                raise Exception
        except:
            log.error('Error: Can not connect to Kytos/Coloring')

    def get_switch_color(self, dpid):
        """ Get the color_field and color_value of a specific
        switch. At every call, queries Coloring Napp to make sure
        colors reflects a possible topology.

        Args:
            dpid: switch.dpid

        Return:
            dict: {'color_field': str, 'color_value': str}
              or
            dict: {} if not found
        """
        self._get_colors()
        try:
            # TODO: remove self._temp_fix_color
            return self._colors[dpid]
        except KeyError:
            return {}
