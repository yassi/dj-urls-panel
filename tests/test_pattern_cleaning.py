"""
Tests for URL pattern cleaning, especially for DRF router patterns.
"""
import unittest
from dj_urls_panel.utils import UrlListInterface


class TestPatternCleaning(unittest.TestCase):
    """Test cases for pattern cleaning with regex anchors."""

    def setUp(self):
        """Set up test instance."""
        self.interface = UrlListInterface()

    def test_strip_regex_anchors(self):
        """Test that regex anchors are properly stripped from pattern components."""
        # Test leading ^
        self.assertEqual(
            self.interface._strip_regex_anchors("^users/"),
            "users/"
        )
        
        # Test trailing $
        self.assertEqual(
            self.interface._strip_regex_anchors("users/$"),
            "users/"
        )
        
        # Test both ^ and $
        self.assertEqual(
            self.interface._strip_regex_anchors("^users/$"),
            "users/"
        )
        
        # Test DRF-style regex pattern with capturing group
        self.assertEqual(
            self.interface._strip_regex_anchors("^users/(?P<pk>[^/.]+)/$"),
            "users/(?P<pk>[^/.]+)/"
        )
        
        # Test pattern without anchors (should be unchanged)
        self.assertEqual(
            self.interface._strip_regex_anchors("api/v1/"),
            "api/v1/"
        )

    def test_clean_pattern_adds_leading_slash(self):
        """Test that _clean_pattern ensures a leading slash."""
        # Pattern without leading slash
        self.assertEqual(
            self.interface._clean_pattern("api/users/"),
            "/api/users/"
        )
        
        # Pattern with leading slash (should be unchanged)
        self.assertEqual(
            self.interface._clean_pattern("/api/users/"),
            "/api/users/"
        )
        
        # Empty pattern
        self.assertEqual(
            self.interface._clean_pattern(""),
            "/"
        )
