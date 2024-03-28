"""Module to test the main napp file."""

from unittest.mock import patch

from kytos.lib.helpers import get_controller_mock


# pylint: disable=too-many-public-methods, too-many-lines
class TestMain:
    """Test the Main class."""

    def setup_method(self):
        """Execute steps before each tests."""

        # The decorator run_on_thread is patched, so methods that listen
        # for events do not run on threads while tested.
        # Decorators have to be patched before the methods that are
        # decorated with them are imported.
        patch("kytos.core.helpers.run_on_thread", lambda x: x).start()
        # pylint: disable=import-outside-toplevel
        from napps.amlight.sdntrace.main import Main

        self.napp = Main(get_controller_mock())
