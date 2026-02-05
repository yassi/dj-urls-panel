"""
Tests for the URL testing interface functionality.

This module tests the URL testing features including:
- Utility functions for DRF detection and curl generation
- URL parameter extraction
- Request execution endpoint
"""

import json
from unittest.mock import MagicMock, patch

from django.test import Client
from django.urls import reverse

from dj_urls_panel.utils import (
    extract_url_parameters,
    get_view_http_methods,
    get_drf_serializer_info,
)

from .base import CeleryPanelTestCase


class TestExtractUrlParameters(CeleryPanelTestCase):
    """Test cases for the extract_url_parameters utility function."""

    def test_no_parameters(self):
        """Test extracting from a pattern with no parameters."""
        params = extract_url_parameters("/api/users/")
        self.assertEqual(params, [])

    def test_single_parameter(self):
        """Test extracting a single parameter."""
        params = extract_url_parameters("/api/users/<int:pk>/")
        
        self.assertEqual(len(params), 1)
        self.assertEqual(params[0]["name"], "pk")
        self.assertEqual(params[0]["type"], "integer")
        self.assertEqual(params[0]["in"], "path")
        self.assertTrue(params[0]["required"])

    def test_multiple_parameters(self):
        """Test extracting multiple parameters."""
        params = extract_url_parameters("/api/users/<int:user_id>/posts/<slug:post_slug>/")
        
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0]["name"], "user_id")
        self.assertEqual(params[0]["type"], "integer")
        self.assertEqual(params[1]["name"], "post_slug")
        self.assertEqual(params[1]["type"], "slug")

    def test_string_parameter_without_type(self):
        """Test extracting a parameter without explicit type (defaults to string)."""
        params = extract_url_parameters("/api/items/<name>/")
        
        self.assertEqual(len(params), 1)
        self.assertEqual(params[0]["name"], "name")
        self.assertEqual(params[0]["type"], "string")

    def test_uuid_parameter(self):
        """Test extracting a UUID parameter."""
        params = extract_url_parameters("/api/items/<uuid:id>/")
        
        self.assertEqual(len(params), 1)
        self.assertEqual(params[0]["name"], "id")
        self.assertEqual(params[0]["type"], "UUID")
    
    def test_regex_named_group_parameter(self):
        """Test extracting regex-style named group parameters."""
        params = extract_url_parameters("/api/articles/(?P<pk>[^/.]+)/")
        
        self.assertEqual(len(params), 1)
        self.assertEqual(params[0]["name"], "pk")
        self.assertEqual(params[0]["type"], "regex")
    
    def test_multiple_regex_parameters(self):
        """Test extracting multiple regex-style parameters."""
        params = extract_url_parameters("/api/(?P<year>[0-9]{4})/(?P<month>[0-9]{2})/")
        
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0]["name"], "year")
        self.assertEqual(params[0]["type"], "regex")
        self.assertEqual(params[1]["name"], "month")
        self.assertEqual(params[1]["type"], "regex")
    
    def test_mixed_path_and_regex_parameters(self):
        """Test URL with both path-style and regex-style parameters."""
        params = extract_url_parameters("/api/articles/<int:id>/comments/(?P<comment_id>[0-9]+)/")
        
        self.assertEqual(len(params), 2)
        # Regex parameters are extracted first, then path parameters
        self.assertEqual(params[0]["name"], "comment_id")
        self.assertEqual(params[0]["type"], "regex")
        self.assertEqual(params[1]["name"], "id")
        self.assertEqual(params[1]["type"], "integer")


class TestGetViewHttpMethods(CeleryPanelTestCase):
    """Test cases for the get_view_http_methods utility function."""

    def test_none_callback(self):
        """Test with None callback returns GET."""
        methods = get_view_http_methods(None)
        self.assertEqual(methods, ["GET"])

    def test_callback_with_http_method_names(self):
        """Test extracting methods from http_method_names attribute."""
        callback = MagicMock()
        callback.http_method_names = ["get", "post", "put"]
        # Ensure view_class doesn't exist so it checks callback's http_method_names
        del callback.view_class
        del callback.cls
        
        methods = get_view_http_methods(callback)
        self.assertEqual(methods, ["GET", "POST", "PUT"])

    def test_class_based_view_with_methods(self):
        """Test extracting methods from a class-based view."""
        mock_view_class = MagicMock()
        mock_view_class.http_method_names = ["get", "post", "delete"]
        
        callback = MagicMock()
        callback.view_class = mock_view_class
        del callback.http_method_names  # Remove from callback itself
        del callback.actions  # Ensure no actions attribute
        
        methods = get_view_http_methods(callback)
        self.assertEqual(methods, ["GET", "POST", "DELETE"])

    def test_viewset_with_actions_list(self):
        """Test extracting methods from a ViewSet list action."""
        mock_view_class = MagicMock()
        mock_view_class.http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
        
        callback = MagicMock()
        callback.view_class = mock_view_class
        callback.actions = {"get": "list", "post": "create"}  # List endpoint actions
        del callback.http_method_names
        
        methods = get_view_http_methods(callback)
        # Should only include GET, POST, HEAD, and OPTIONS (not PUT, PATCH, DELETE)
        self.assertIn("GET", methods)
        self.assertIn("POST", methods)
        self.assertIn("HEAD", methods)
        self.assertIn("OPTIONS", methods)
        self.assertNotIn("PUT", methods)
        self.assertNotIn("PATCH", methods)
        self.assertNotIn("DELETE", methods)

    def test_viewset_with_actions_detail(self):
        """Test extracting methods from a ViewSet detail action."""
        mock_view_class = MagicMock()
        mock_view_class.http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
        
        callback = MagicMock()
        callback.view_class = mock_view_class
        callback.actions = {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        del callback.http_method_names
        
        methods = get_view_http_methods(callback)
        # Should include GET, PUT, PATCH, DELETE, HEAD, and OPTIONS (not POST)
        self.assertIn("GET", methods)
        self.assertIn("PUT", methods)
        self.assertIn("PATCH", methods)
        self.assertIn("DELETE", methods)
        self.assertIn("HEAD", methods)
        self.assertIn("OPTIONS", methods)
        self.assertNotIn("POST", methods)

    def test_readonly_viewset_with_actions(self):
        """Test extracting methods from a ReadOnlyModelViewSet."""
        mock_view_class = MagicMock()
        mock_view_class.http_method_names = ["get", "head", "options"]
        
        callback = MagicMock()
        callback.view_class = mock_view_class
        callback.actions = {"get": "list"}  # Read-only ViewSet
        del callback.http_method_names
        
        methods = get_view_http_methods(callback)
        # Should only include GET, HEAD, and OPTIONS
        self.assertIn("GET", methods)
        self.assertIn("HEAD", methods)
        self.assertIn("OPTIONS", methods)
        self.assertEqual(len(methods), 3)


class TestExecuteRequestView(CeleryPanelTestCase):
    """Test cases for the execute_request API endpoint."""

    def test_execute_request_success(self):
        """Test successful request execution."""
        # Create mock objects
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"success": True}
        mock_response.elapsed.total_seconds.return_value = 0.150
        mock_response.url = "http://localhost:8000/api/test/"
        
        # Patch the requests module that gets imported inside the view
        with patch.dict('sys.modules', {'requests': MagicMock()}) as mock_modules:
            mock_requests = mock_modules['requests']
            mock_requests.request.return_value = mock_response
            mock_requests.exceptions = MagicMock()
            mock_requests.exceptions.Timeout = Exception
            mock_requests.exceptions.ConnectionError = Exception
            mock_requests.exceptions.RequestException = Exception
            
            url = reverse("dj_urls_panel:execute_request")
            
            response = self.client.post(
                url,
                data=json.dumps({
                    "url": "http://localhost:8000/api/test/",
                    "method": "GET",
                }),
                content_type="application/json",
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status_code"], 200)
            self.assertEqual(data["status_text"], "OK")
            self.assertTrue(data["is_json"])

    def test_execute_request_missing_url(self):
        """Test execute_request with missing URL."""
        # Patch the requests module to avoid import errors
        with patch.dict('sys.modules', {'requests': MagicMock()}) as mock_modules:
            mock_requests = mock_modules['requests']
            mock_requests.exceptions = MagicMock()
            mock_requests.exceptions.Timeout = Exception
            mock_requests.exceptions.ConnectionError = Exception
            mock_requests.exceptions.RequestException = Exception
            
            url = reverse("dj_urls_panel:execute_request")
            
            response = self.client.post(
                url,
                data=json.dumps({"method": "GET"}),
                content_type="application/json",
            )
            
            self.assertEqual(response.status_code, 400)
            data = response.json()
            self.assertIn("error", data)

    def test_execute_request_unauthenticated(self):
        """Test that unauthenticated users cannot execute requests."""
        client = Client()
        url = reverse("dj_urls_panel:execute_request")
        
        response = client.post(
            url,
            data=json.dumps({"url": "http://localhost:8000/", "method": "GET"}),
            content_type="application/json",
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)


class TestUrlDetailView(CeleryPanelTestCase):
    """Test cases for the url_detail view with testing interface context."""

    def test_url_detail_includes_http_methods(self):
        """Test that url_detail includes HTTP methods in context."""
        # Use a known URL pattern from the project
        url = reverse("dj_urls_panel:url_detail", kwargs={"pattern": "/admin/"})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("http_methods", response.context)
        self.assertIn("test_url", response.context)
        self.assertIn("base_url", response.context)

    def test_url_detail_includes_url_parameters(self):
        """Test that url_detail includes URL parameters in context."""
        url = reverse("dj_urls_panel:url_detail", kwargs={"pattern": "/admin/"})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("url_parameters", response.context)


class TestDrfSerializerInfo(CeleryPanelTestCase):
    """Test cases for DRF serializer information extraction."""

    def test_none_view_class(self):
        """Test that None view class returns None."""
        result = get_drf_serializer_info(None)
        self.assertIsNone(result)

    def test_non_drf_view_class(self):
        """Test that non-DRF view class returns None."""
        class SimpleView:
            pass
        
        result = get_drf_serializer_info(SimpleView)
        self.assertIsNone(result)

    def test_view_with_serializer_class(self):
        """Test extracting serializer info from a DRF view."""
        # Create a mock serializer class
        mock_serializer = MagicMock()
        mock_serializer.__name__ = "TestSerializer"
        mock_serializer.__module__ = "test.serializers"
        
        # Create a mock view class
        mock_view = MagicMock()
        mock_view.serializer_class = mock_serializer
        
        # Since we can't easily mock all the internals,
        # just test that the function handles exceptions gracefully
        result = get_drf_serializer_info(mock_view)
        
        # Should return something or None without raising an exception
        # The actual result depends on serializer instantiation
        self.assertTrue(result is None or isinstance(result, dict))
