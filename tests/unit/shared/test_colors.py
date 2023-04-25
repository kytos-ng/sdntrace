"""Test the /shared/colors.py."""
from unittest import TestCase
from unittest.mock import patch, MagicMock
from napps.amlight.sdntrace.shared.colors import Colors


# pylint: disable=protected-access
class TestColors(TestCase):
    """Test the Colors class."""

    @patch("requests.get")
    def test_rest_colors(self, mock_request_get):
        """Test rest call to /colors to retrieve all switches color."""
        result = MagicMock()
        result.content = (
            '{"colors": {'
            '"aa:00:00:00:00:00:00:11": {"color_field": "dl_src", '
            '"color_value": "ee:ee:ee:ee:01:2c"},'
            '"aa:00:00:00:00:00:00:12": {"color_field": "dl_src", '
            '"color_value": "ee:ee:ee:ee:01:2d"}'
            "}}"
        )
        result.status_code = 200

        mock_request_get.return_value = result

        # Call rest /colors
        color_manager = Colors()
        colors = color_manager._colors

        mock_request_get.assert_called_once()
        self.assertEqual(colors["aa:00:00:00:00:00:00:11"]["color_field"], "dl_src")
        self.assertEqual(
            colors["aa:00:00:00:00:00:00:11"]["color_value"],
            "ee:ee:ee:ee:01:2c",
        )
        self.assertEqual(colors["aa:00:00:00:00:00:00:12"]["color_field"], "dl_src")
        self.assertEqual(
            colors["aa:00:00:00:00:00:00:12"]["color_value"],
            "ee:ee:ee:ee:01:2d",
        )

    @patch("requests.get")
    def test_rest_colors_without_switches(self, mock_request_get):
        """Test rest call to /colors without switches."""
        result = MagicMock()
        result.content = '{"colors": {}}'
        result.status_code = 200

        mock_request_get.return_value = result

        # Call rest /colors
        color_manager = Colors()
        colors = color_manager._colors

        mock_request_get.assert_called_once()
        self.assertEqual(colors, {})

    @patch("requests.get")
    def test_get_switch_colors(self, mock_request_get):
        """Test rest call to /colors to retrieve all switches color."""
        result = MagicMock()
        result.content = (
            '{"colors": {'
            '"aa:00:00:00:00:00:00:11": {"color_field": "dl_src", '
            '"color_value": "ee:ee:ee:ee:01:2c"},'
            '"aa:00:00:00:00:00:00:12": {"color_field": "dl_src", '
            '"color_value": "ee:ee:ee:ee:01:2d"}'
            "}}"
        )
        result.status_code = 200

        mock_request_get.return_value = result

        # Call rest /colors
        color_manager = Colors()
        self.assertEqual(mock_request_get.call_count, 1)

        color = color_manager.get_switch_color("aa:00:00:00:00:00:00:11")

        self.assertEqual(mock_request_get.call_count, 2)
        self.assertEqual(color["color_field"], "dl_src")
        self.assertEqual(color["color_value"], "ee:ee:ee:ee:01:2c")

        color = color_manager.get_switch_color("aa:00:00:00:00:00:00:12")

        self.assertEqual(mock_request_get.call_count, 3)
        self.assertEqual(color["color_field"], "dl_src")
        self.assertEqual(color["color_value"], "ee:ee:ee:ee:01:2d")
