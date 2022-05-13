"""Module to test the main napp file."""
from unittest import TestCase
from unittest.mock import patch

from kytos.lib.helpers import (get_controller_mock)


# pylint: disable=too-many-public-methods, too-many-lines
class TestMain(TestCase):
    """Test the Main class."""

    def setUp(self):
        """Execute steps before each tests.

        Set the server_name_url_url from amlight/sdntrace
        """
        self.server_name_url = "http://localhost:8181/api/amlight/sdntrace"

        # The decorator run_on_thread is patched, so methods that listen
        # for events do not run on threads while tested.
        # Decorators have to be patched before the methods that are
        # decorated with them are imported.
        patch("kytos.core.helpers.run_on_thread", lambda x: x).start()
        # pylint: disable=import-outside-toplevel
        from napps.amlight.sdntrace.main import Main
        self.napp = Main(get_controller_mock())

    @staticmethod
    def get_napp_urls(napp):
        """Return the amlight/sdntrace urls.

        The urls will be like:

        urls = [
            (options, methods, url)
        ]

        """
        controller = napp.controller
        controller.api_server.register_napp_endpoints(napp)

        urls = []
        for rule in controller.api_server.app.url_map.iter_rules():
            options = {}
            for arg in rule.arguments:
                options[arg] = f"[{0}]".format(arg)

            if f"{napp.username}/{napp.name}" in str(rule):
                urls.append((options, rule.methods, f"{str(rule)}"))

        return urls

    def test_verify_api_urls(self):
        """Verify all APIs registered."""

        expected_urls = [
            (
                {},
                {"OPTIONS", "HEAD", "PUT", "GET"},
                "/api/amlight/sdntrace/trace/ "),
            (
                {},
                {"OPTIONS", "PUT"},
                "/api/amlight/sdntrace/trace/ "),
            (
                {"trace_id": "[trace_id]"},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/sdntrace/trace/"
            ),
            (
                {},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/sdntrace/stats/",),
            (
                {},
                {"OPTIONS", "HEAD", "GET"},
                "/api/amlight/sdntrace/settings/",),
        ]
        urls = self.get_napp_urls(self.napp)
        self.assertEqual(len(expected_urls), len(urls))
