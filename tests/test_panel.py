"""
Tests for the UrlsPanel plugin declaration (dj_urls_panel.panel).
"""

from django.test import SimpleTestCase

from dj_urls_panel.conf import panel_config
from dj_urls_panel.panel import UrlsPanel


class TestUrlsPanel(SimpleTestCase):
    """Test cases for the UrlsPanel PanelPlugin subclass."""

    def test_validate_passes(self):
        """validate() should not raise since all required attrs are set."""
        panel = UrlsPanel()
        panel.validate()  # Raises on failure; no assertion needed.

    def test_get_config_returns_panel_config(self):
        """get_config() returns the module-level PanelConfig singleton."""
        panel = UrlsPanel()
        self.assertIs(panel.get_config(), panel_config)
