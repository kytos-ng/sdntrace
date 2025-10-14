"""
    Module to interact with Coloring Napp.
"""


import httpx
from kytos.core import log
from napps.amlight.sdntrace import settings


class Colors(object):
    """ Class to handle the gathering of colors from
    amlight/coloring Napp

    """

    def __init__(self):
        """ Instantiate Colors and get list of colors
        """
        self._url = settings.COLORS_URL
        self._colors = dict()

    def _get_colors(self):
        """ Get list of colors
        """
        try:
            result = httpx.get(self._url)
            if result.status_code == 200:
                result = result.json()
                self._colors = result['colors']
            else:
                raise Exception
        except Exception as err:  # pylint: disable=broad-except
            log.error(f'Error: Can not connect to Kytos/Coloring: {err}')

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
            return self._colors[dpid]
        except KeyError:
            return {}

    async def _aget_colors(self):
        """Get list of colors asynchronously."""
        async with httpx.AsyncClient() as client:
            result = await client.get(self._url)
            if result.is_server_error or result.status_code >= 400:
                log.error(f'Error ocurred when getting colors: {result.text}')
            result = result.json()
            self._colors = result['colors']

    async def aget_switch_color(self, dpid):
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
        await self._aget_colors()
        try:
            return self._colors[dpid]
        except KeyError:
            return {}