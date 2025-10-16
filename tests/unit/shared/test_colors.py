"""Test the /shared/colors.py."""

from unittest.mock import patch, MagicMock
from napps.amlight.sdntrace.shared.colors import Colors


# pylint: disable=protected-access
class TestColors:
    """Test the Colors class."""

    @patch("httpx.get")
    def test_get_switch_colors_without_switches(self, mock_request_get):
        """Test rest call to /colors without switches."""
        result = MagicMock()
        result.json.return_value = '{"colors": {}}'
        result.status_code = 200

        mock_request_get.return_value = result

        # Call rest /colors
        color_manager = Colors()
        color_manager.get_switch_color("mock_switch")
        colors = color_manager._colors

        mock_request_get.assert_called_once()
        assert colors == {}

    @patch("httpx.get")
    def test_get_switch_colors(self, mock_request_get):
        """Test rest call to /colors to retrieve all switches color."""
        result = MagicMock()
        result.json.return_value = {
            "colors": {
                "aa:00:00:00:00:00:00:11": {
                    "color_field": "dl_src",
                    "color_value": "ee:ee:ee:ee:01:2c",
                },
                "aa:00:00:00:00:00:00:12": {
                    "color_field": "dl_src",
                    "color_value": "ee:ee:ee:ee:01:2d",
                },
            }
        }
        result.status_code = 200

        mock_request_get.return_value = result

        # Call rest /colors
        color_manager = Colors()

        color = color_manager.get_switch_color("aa:00:00:00:00:00:00:11")

        assert mock_request_get.call_count == 1
        assert color["color_field"] == "dl_src"
        assert color["color_value"] == "ee:ee:ee:ee:01:2c"

        color = color_manager.get_switch_color("aa:00:00:00:00:00:00:12")

        assert mock_request_get.call_count == 2
        assert color["color_field"] == "dl_src"
        assert color["color_value"] == "ee:ee:ee:ee:01:2d"

    @patch("httpx.AsyncClient.get")
    async def test_aget_switch_colors(self, mock_request_get):
        """Test rest call to /colors to retrieve all switches color."""
        result = MagicMock()
        result.json.return_value = {
            "colors": {
                "aa:00:00:00:00:00:00:11": {
                    "color_field": "dl_src",
                    "color_value": "ee:ee:ee:ee:01:2c",
                },
                "aa:00:00:00:00:00:00:12": {
                    "color_field": "dl_src",
                    "color_value": "ee:ee:ee:ee:01:2d",
                },
            }
        }
        result.status_code = 200
        result.is_server_error = False

        mock_request_get.return_value = result

        # Call rest /colors
        color_manager = Colors()

        color = await color_manager.aget_switch_color("aa:00:00:00:00:00:00:11")

        assert mock_request_get.call_count == 1
        assert color["color_field"] == "dl_src"
        assert color["color_value"] == "ee:ee:ee:ee:01:2c"

        color = await color_manager.aget_switch_color("aa:00:00:00:00:00:00:12")

        assert mock_request_get.call_count == 2
        assert color["color_field"] == "dl_src"
        assert color["color_value"] == "ee:ee:ee:ee:01:2d"
