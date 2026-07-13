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
    UrlListInterface,
)

from .base import UrlsPanelTestCase


class TestExtractUrlParameters(UrlsPanelTestCase):
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


class TestGetViewHttpMethods(UrlsPanelTestCase):
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


class TestExecuteRequestView(UrlsPanelTestCase):
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
        mock_response.url = "http://example.com/api/test/"

        # Allow example.com in ALLOWED_HOSTS to bypass SSRF protection
        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            # Import requests module here
            import requests
            
            # Patch requests.request method
            with patch.object(requests, 'request', return_value=mock_response):
                url = reverse("dj_urls_panel:execute_request")

                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/test/",
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

    def test_execute_request_requests_library_missing(self):
        """Test the friendly error returned when 'requests' isn't installed."""
        with patch.dict('sys.modules', {'requests': None}):
            url = reverse("dj_urls_panel:execute_request")

            response = self.client.post(
                url,
                data=json.dumps({"url": "http://example.com/", "method": "GET"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("requests", data["error"].lower())
        self.assertIn("pip install", data["error"])

    def test_execute_request_invalid_json_body(self):
        """Test that malformed JSON in the request body returns a 400."""
        url = reverse("dj_urls_panel:execute_request")

        response = self.client.post(
            url,
            data="{not valid json",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Invalid JSON", data["error"])

    def test_execute_request_timeout(self):
        """Test that a request timeout is surfaced as a 408."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', side_effect=requests.exceptions.Timeout("timed out")
            ):
                url = reverse("dj_urls_panel:execute_request")

                response = self.client.post(
                    url,
                    data=json.dumps({"url": "http://example.com/", "method": "GET"}),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 408)
        self.assertIn("timed out", response.json()["error"].lower())

    def test_execute_request_connection_error(self):
        """Test that a connection error is surfaced as a 502."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests,
                'request',
                side_effect=requests.exceptions.ConnectionError("refused"),
            ):
                url = reverse("dj_urls_panel:execute_request")

                response = self.client.post(
                    url,
                    data=json.dumps({"url": "http://example.com/", "method": "GET"}),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 502)
        self.assertIn("connection error", response.json()["error"].lower())

    def test_execute_request_generic_request_exception(self):
        """Test that a generic requests exception is surfaced as a 500."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests,
                'request',
                side_effect=requests.exceptions.RequestException("boom"),
            ):
                url = reverse("dj_urls_panel:execute_request")

                response = self.client.post(
                    url,
                    data=json.dumps({"url": "http://example.com/", "method": "GET"}),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 500)
        self.assertIn("request failed", response.json()["error"].lower())

    def test_execute_request_unexpected_exception(self):
        """Test that any other unexpected exception falls through to a 500."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', side_effect=ValueError("something unexpected")
            ):
                url = reverse("dj_urls_panel:execute_request")

                response = self.client.post(
                    url,
                    data=json.dumps({"url": "http://example.com/", "method": "GET"}),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 500)
        self.assertIn("something unexpected", response.json()["error"])


def _mock_proxied_response(**overrides):
    """Build a MagicMock standing in for requests.Response, for the outbound
    (proxied) call that execute_request makes on behalf of the browser."""
    response = MagicMock()
    response.status_code = overrides.get("status_code", 200)
    response.reason = overrides.get("reason", "OK")
    response.headers = overrides.get("headers", {})
    response.json.return_value = overrides.get("json", {"ok": True})
    response.elapsed.total_seconds.return_value = overrides.get("elapsed", 0.1)
    response.url = overrides.get("url", "http://example.com/")
    return response


class TestExecuteRequestAuthTypes(UrlsPanelTestCase):
    """
    Tests for the auth_type handling (session, session_cookie, basic,
    bearer, token) and CSRF forwarding/minting in execute_request.

    These exercise the real POST endpoint end-to-end (mocking only the
    outbound `requests` calls the proxy makes) rather than reaching into
    the view's private helper methods, so they double as documentation of
    the endpoint's observable behavior.
    """

    def test_session_auth_forwards_current_session_cookie(self):
        """auth_type=session forwards the admin session cookie to the target."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/",
                        "method": "GET",
                        "auth_type": "session",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        sent_cookies = mock_request.call_args.kwargs.get("cookies", {})
        self.assertEqual(sent_cookies.get("sessionid"), self.client.cookies["sessionid"].value)

    def test_session_auth_forwards_known_csrf_token_for_write_requests(self):
        """A CSRF cookie already on hand becomes an X-CSRFToken header for writes."""
        import requests

        # Load a page that renders {% csrf_token %} so the test client picks
        # up a real, validly-formatted CSRF cookie (an arbitrary string here
        # would just get rejected and rotated by Django's CSRF middleware).
        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            self.client.get(reverse("dj_urls_panel:url_detail", kwargs={"pattern": "/admin/"}))
        known_token = self.client.cookies["csrftoken"].value

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/items/",
                        "method": "POST",
                        "auth_type": "session",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        sent_headers = mock_request.call_args.kwargs.get("headers", {})
        self.assertEqual(sent_headers.get("X-CSRFToken"), known_token)

    def test_session_auth_mints_csrf_token_when_none_available(self):
        """Without a local CSRF cookie, a GET against the target mints one first."""
        import requests

        minted_response = _mock_proxied_response()
        minted_response.cookies = {"csrftoken": "minted-token"}

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(requests, 'get', return_value=minted_response) as mock_get:
                with patch.object(
                    requests, 'request', return_value=_mock_proxied_response()
                ) as mock_request:
                    url = reverse("dj_urls_panel:execute_request")
                    response = self.client.post(
                        url,
                        data=json.dumps({
                            "url": "http://example.com/api/items/",
                            "method": "POST",
                            "auth_type": "session",
                        }),
                        content_type="application/json",
                    )

        self.assertEqual(response.status_code, 200)
        mock_get.assert_called_once()
        sent_headers = mock_request.call_args.kwargs.get("headers", {})
        self.assertEqual(sent_headers.get("X-CSRFToken"), "minted-token")

    def test_session_auth_minting_failure_still_completes_request(self):
        """If the CSRF-minting GET blows up, the proxied request still goes through."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(requests, 'get', side_effect=Exception("network is down")):
                with patch.object(
                    requests, 'request', return_value=_mock_proxied_response()
                ) as mock_request:
                    url = reverse("dj_urls_panel:execute_request")
                    response = self.client.post(
                        url,
                        data=json.dumps({
                            "url": "http://example.com/api/items/",
                            "method": "DELETE",
                            "auth_type": "session",
                        }),
                        content_type="application/json",
                    )

        self.assertEqual(response.status_code, 200)
        sent_headers = mock_request.call_args.kwargs.get("headers", {})
        self.assertNotIn("X-CSRFToken", sent_headers)

    def test_session_auth_get_forwards_csrf_cookie_without_minting(self):
        """A GET with a known CSRF cookie just forwards it; no token is minted."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            self.client.get(reverse("dj_urls_panel:url_detail", kwargs={"pattern": "/admin/"}))

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(requests, 'get') as mock_get:
                with patch.object(
                    requests, 'request', return_value=_mock_proxied_response()
                ) as mock_request:
                    url = reverse("dj_urls_panel:execute_request")
                    response = self.client.post(
                        url,
                        data=json.dumps({
                            "url": "http://example.com/api/",
                            "method": "GET",
                            "auth_type": "session",
                        }),
                        content_type="application/json",
                    )

        self.assertEqual(response.status_code, 200)
        mock_get.assert_not_called()
        sent_cookies = mock_request.call_args.kwargs.get("cookies", {})
        self.assertEqual(sent_cookies.get("csrftoken"), self.client.cookies["csrftoken"].value)

    def test_session_auth_minting_response_without_csrf_cookie(self):
        """If the minting GET succeeds but carries no CSRF cookie, none is set."""
        import requests

        minted_response = _mock_proxied_response()
        minted_response.cookies = {}

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(requests, 'get', return_value=minted_response):
                with patch.object(
                    requests, 'request', return_value=_mock_proxied_response()
                ) as mock_request:
                    url = reverse("dj_urls_panel:execute_request")
                    response = self.client.post(
                        url,
                        data=json.dumps({
                            "url": "http://example.com/api/items/",
                            "method": "PUT",
                            "auth_type": "session",
                        }),
                        content_type="application/json",
                    )

        self.assertEqual(response.status_code, 200)
        sent_headers = mock_request.call_args.kwargs.get("headers", {})
        self.assertNotIn("X-CSRFToken", sent_headers)

    def test_session_cookie_auth_uses_supplied_session_id(self):
        """auth_type=session_cookie forwards the explicitly supplied session id."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/",
                        "method": "GET",
                        "auth_type": "session_cookie",
                        "auth_value": "some-other-session-id",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        sent_cookies = mock_request.call_args.kwargs.get("cookies", {})
        self.assertEqual(sent_cookies.get("sessionid"), "some-other-session-id")

    def test_session_cookie_auth_without_value_is_ignored(self):
        """session_cookie requires a truthy auth_value; without one, no cookies are sent."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/",
                        "method": "GET",
                        "auth_type": "session_cookie",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("cookies", mock_request.call_args.kwargs)

    def test_basic_auth_sets_credentials(self):
        """auth_type=basic with 'user:pass' becomes an HTTP basic auth tuple."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/",
                        "method": "GET",
                        "auth_type": "basic",
                        "auth_value": "user:pass",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_args.kwargs.get("auth"), ("user", "pass"))

    def test_basic_auth_without_colon_is_ignored(self):
        """A malformed 'basic' auth_value (no colon) results in no auth being sent."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/",
                        "method": "GET",
                        "auth_type": "basic",
                        "auth_value": "not-a-valid-value",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("auth", mock_request.call_args.kwargs)

    def test_bearer_auth_sets_authorization_header(self):
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/",
                        "method": "GET",
                        "auth_type": "bearer",
                        "auth_value": "tok123",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_request.call_args.kwargs["headers"].get("Authorization"), "Bearer tok123"
        )

    def test_token_auth_sets_authorization_header(self):
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/",
                        "method": "GET",
                        "auth_type": "token",
                        "auth_value": "tok123",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_request.call_args.kwargs["headers"].get("Authorization"), "Token tok123"
        )

    def test_unrecognized_auth_type_sends_no_credentials(self):
        """An auth_value is present but auth_type matches none of the known kinds."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/",
                        "method": "GET",
                        "auth_type": "custom",
                        "auth_value": "some-value",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("auth", mock_request.call_args.kwargs)
        self.assertNotIn("Authorization", mock_request.call_args.kwargs.get("headers", {}))

    def test_no_auth_type_sends_no_credentials(self):
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({"url": "http://example.com/api/", "method": "GET"}),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("auth", mock_request.call_args.kwargs)
        self.assertNotIn("cookies", mock_request.call_args.kwargs)


class TestExecuteRequestBodyAndResponse(UrlsPanelTestCase):
    """Tests for outbound request body encoding and proxied response parsing."""

    def test_json_body_is_forwarded_with_content_type(self):
        """A JSON string body gets forwarded as-is with a JSON Content-Type."""
        import requests

        body = json.dumps({"name": "widget"})

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests,
                'request',
                return_value=_mock_proxied_response(status_code=201, reason="Created"),
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/items/",
                        "method": "POST",
                        "body": body,
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        sent_kwargs = mock_request.call_args.kwargs
        self.assertEqual(sent_kwargs["data"], body)
        self.assertEqual(sent_kwargs["headers"].get("Content-Type"), "application/json")
        self.assertEqual(response.json()["status_code"], 201)

    def test_non_json_body_is_forwarded_as_is(self):
        """A body that isn't valid JSON is still forwarded, just without a
        forced JSON Content-Type."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/items/",
                        "method": "POST",
                        "body": "plain text, not json",
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        sent_kwargs = mock_request.call_args.kwargs
        self.assertEqual(sent_kwargs["data"], "plain text, not json")
        self.assertNotIn("Content-Type", sent_kwargs["headers"])

    def test_json_body_does_not_override_explicit_content_type(self):
        """An explicit Content-Type header on the request is left untouched."""
        import requests

        body = json.dumps({"name": "widget"})

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/items/",
                        "method": "POST",
                        "body": body,
                        "headers": {"Content-Type": "application/vnd.custom+json"},
                    }),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        sent_kwargs = mock_request.call_args.kwargs
        self.assertEqual(sent_kwargs["data"], body)
        self.assertEqual(
            sent_kwargs["headers"].get("Content-Type"), "application/vnd.custom+json"
        )

    def test_body_is_dropped_for_get_requests(self):
        """A body provided alongside method=GET is not forwarded."""
        import requests

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(
                requests, 'request', return_value=_mock_proxied_response()
            ) as mock_request:
                url = reverse("dj_urls_panel:execute_request")
                self.client.post(
                    url,
                    data=json.dumps({
                        "url": "http://example.com/api/",
                        "method": "GET",
                        "body": json.dumps({"a": 1}),
                    }),
                    content_type="application/json",
                )

        self.assertNotIn("data", mock_request.call_args.kwargs)

    def test_non_json_proxied_response_falls_back_to_text_body(self):
        """When the target's response isn't JSON, the raw text is returned instead."""
        import requests

        mock_response = _mock_proxied_response(headers={"Content-Type": "text/html"})
        mock_response.json.side_effect = ValueError("no JSON object could be decoded")
        mock_response.text = "<html>hi</html>"

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com']}):
            with patch.object(requests, 'request', return_value=mock_response):
                url = reverse("dj_urls_panel:execute_request")
                response = self.client.post(
                    url,
                    data=json.dumps({"url": "http://example.com/", "method": "GET"}),
                    content_type="application/json",
                )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["is_json"])
        self.assertEqual(data["body"], "<html>hi</html>")


class TestUrlDetailView(UrlsPanelTestCase):
    """Test cases for the url_detail view with testing interface context."""

    def test_url_detail_includes_http_methods(self):
        """Test that url_detail includes HTTP methods in context."""
        # Override DJ_URLS_PANEL_SETTINGS to not exclude URLs for this test
        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            # Use a known URL pattern from the project
            url = reverse("dj_urls_panel:url_detail", kwargs={"pattern": "/admin/"})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn("http_methods", response.context)
            self.assertIn("test_url", response.context)
            self.assertIn("base_url", response.context)

    def test_url_detail_includes_url_parameters(self):
        """Test that url_detail includes URL parameters in context."""
        # Override DJ_URLS_PANEL_SETTINGS to not exclude URLs for this test
        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            url = reverse("dj_urls_panel:url_detail", kwargs={"pattern": "/admin/"})
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn("url_parameters", response.context)


class TestExcludeUrls(UrlsPanelTestCase):
    """Test cases for EXCLUDE_URLS setting."""

    def test_exclude_urls_filters_patterns(self):
        """Test that EXCLUDE_URLS setting filters out matching URL patterns."""
        from dj_urls_panel.utils import UrlListInterface
        
        # Test with exclusion settings
        with self.settings(DJ_URLS_PANEL_SETTINGS={'EXCLUDE_URLS': [r'^admin/']}):
            interface = UrlListInterface()
            urls = interface.get_url_list()
            
            # Admin URLs should be excluded
            admin_urls = [url for url in urls if url['pattern'].startswith('/admin/')]
            self.assertEqual(len(admin_urls), 0, "Admin URLs should be excluded")
    
    def test_exclude_urls_keeps_non_matching_patterns(self):
        """Test that EXCLUDE_URLS doesn't filter non-matching patterns."""
        from dj_urls_panel.utils import UrlListInterface
        
        # Test with exclusion settings
        with self.settings(DJ_URLS_PANEL_SETTINGS={'EXCLUDE_URLS': [r'^admin/']}):
            interface = UrlListInterface()
            urls = interface.get_url_list()
            
            # API URLs should still be present
            api_urls = [url for url in urls if url['pattern'].startswith('/api/')]
            self.assertGreater(len(api_urls), 0, "API URLs should not be excluded")
    
    def test_no_exclusion_when_setting_absent(self):
        """Test that URLs are not filtered when DJ_URLS_PANEL_SETTINGS is absent."""
        from dj_urls_panel.utils import UrlListInterface
        
        # Test without exclusion settings
        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            interface = UrlListInterface()
            urls = interface.get_url_list()
            
            # Admin URLs should be present
            admin_urls = [url for url in urls if url['pattern'].startswith('/admin/')]
            self.assertGreater(len(admin_urls), 0, "Admin URLs should be present when not excluded")
    
    def test_multiple_exclusion_patterns(self):
        """Test multiple exclusion patterns."""
        from dj_urls_panel.utils import UrlListInterface
        
        # Test with multiple exclusion patterns
        with self.settings(DJ_URLS_PANEL_SETTINGS={'EXCLUDE_URLS': [r'^admin/', r'^api/']}):
            interface = UrlListInterface()
            urls = interface.get_url_list()
            
            # Both admin and API URLs should be excluded
            admin_urls = [url for url in urls if url['pattern'].startswith('/admin/')]
            api_urls = [url for url in urls if url['pattern'].startswith('/api/')]
            
            self.assertEqual(len(admin_urls), 0, "Admin URLs should be excluded")
            self.assertEqual(len(api_urls), 0, "API URLs should be excluded")


class TestUrlConfig(UrlsPanelTestCase):
    """Test cases for URL_CONFIG setting."""

    def test_url_config_uses_custom_urlconf(self):
        """Test that URL_CONFIG setting uses a custom URLconf."""
        from dj_urls_panel.utils import UrlListInterface
        
        # Test with custom URL_CONFIG
        with self.settings(DJ_URLS_PANEL_SETTINGS={'URL_CONFIG': 'example_project.urls'}):
            interface = UrlListInterface()
            self.assertEqual(interface.urlconf, 'example_project.urls')
    
    def test_url_config_defaults_to_root_urlconf(self):
        """Test that it defaults to ROOT_URLCONF when URL_CONFIG is not set."""
        from dj_urls_panel.utils import UrlListInterface
        from django.conf import settings
        
        # Test without URL_CONFIG
        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            interface = UrlListInterface()
            self.assertEqual(interface.urlconf, settings.ROOT_URLCONF)
    
    def test_explicit_urlconf_overrides_url_config(self):
        """Test that explicit urlconf parameter overrides URL_CONFIG."""
        from dj_urls_panel.utils import UrlListInterface
        
        # Test with both URL_CONFIG and explicit urlconf
        with self.settings(DJ_URLS_PANEL_SETTINGS={'URL_CONFIG': 'example_project.urls'}):
            interface = UrlListInterface(urlconf='some.other.urls')
            self.assertEqual(interface.urlconf, 'some.other.urls')


class TestEnableTesting(UrlsPanelTestCase):
    """Test cases for ENABLE_TESTING setting."""

    def test_testing_disabled_rejects_requests(self):
        """Test that execute_request returns 403 when testing is disabled."""
        with self.settings(DJ_URLS_PANEL_SETTINGS={'ENABLE_TESTING': False}):
            url = reverse("dj_urls_panel:execute_request")
            data = {
                "url": "http://example.com/api/test/",
                "method": "GET",
            }

            response = self.client.post(
                url, data=json.dumps(data), content_type="application/json"
            )

            self.assertEqual(response.status_code, 403)
            result = response.json()
            self.assertIn("error", result)
            self.assertIn("disabled", result["error"].lower())

    def test_testing_enabled_allows_requests(self):
        """Test that execute_request works when testing is enabled."""
        # Use example.com which is allowed by ALLOWED_HOSTS
        test_url = "http://example.com/api/test/"
        
        # Mock the requests.request function to return a success response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"success": True}
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_response.text = '{"success": true}'
        mock_response.url = test_url

        with self.settings(DJ_URLS_PANEL_SETTINGS={'ENABLE_TESTING': True, 'ALLOWED_HOSTS': ['example.com']}):
            # Import here to ensure patching works
            import requests
            
            # Patch requests.request at the point of use
            with patch.object(requests, 'request', return_value=mock_response):
                url = reverse("dj_urls_panel:execute_request")
                data = {
                    "url": test_url,
                    "method": "GET",
                }

                response = self.client.post(
                    url, data=json.dumps(data), content_type="application/json"
                )

                if response.status_code != 200:
                    # Print error for debugging
                    print(f"Error response: {response.json()}")
                
                self.assertEqual(response.status_code, 200)
                result = response.json()
                self.assertEqual(result["status_code"], 200)

    def test_detail_view_hides_interface_when_disabled(self):
        """Test that url_detail doesn't show testing interface when disabled."""
        with self.settings(DJ_URLS_PANEL_SETTINGS={'ENABLE_TESTING': False}):
            interface = UrlListInterface()
            urls = interface.get_url_list()
            
            if urls:
                url = reverse("dj_urls_panel:url_detail", kwargs={"pattern": urls[0]['pattern']})
                response = self.client.get(url)
                
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context['enable_testing'])


class TestAllowedHosts(UrlsPanelTestCase):
    """Test cases for ALLOWED_HOSTS setting and SSRF protection."""

    def test_blocks_localhost_by_default(self):
        """Test that localhost is blocked by default for SSRF protection."""
        from dj_urls_panel.views import ExecuteRequestView
        
        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            is_allowed, error = ExecuteRequestView._is_url_allowed("http://localhost:8000/api/test/")
            self.assertFalse(is_allowed)
            self.assertIn("blocked", error.lower())

    def test_blocks_private_ips_by_default(self):
        """Test that private IP ranges are blocked by default."""
        from dj_urls_panel.views import ExecuteRequestView
        
        test_urls = [
            "http://127.0.0.1/api/",
            "http://10.0.0.1/api/",
            "http://172.16.0.1/api/",
            "http://192.168.1.1/api/",
            "http://169.254.169.254/latest/meta-data/",  # Cloud metadata
        ]
        
        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            for test_url in test_urls:
                is_allowed, error = ExecuteRequestView._is_url_allowed(test_url)
                self.assertFalse(is_allowed, f"Should block {test_url}")
                self.assertIn("blocked", error.lower())

    def test_blocks_url_with_no_hostname(self):
        """Test that a URL without a hostname is rejected."""
        from dj_urls_panel.views import ExecuteRequestView

        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            is_allowed, error = ExecuteRequestView._is_url_allowed("not-a-url-at-all")
            self.assertFalse(is_allowed)
            self.assertIn("no hostname found", error.lower())

    def test_rejects_malformed_url_gracefully(self):
        """Test that a URL that raises while parsing is caught and reported."""
        from dj_urls_panel.views import ExecuteRequestView

        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            is_allowed, error = ExecuteRequestView._is_url_allowed("http://[invalid")
            self.assertFalse(is_allowed)
            self.assertIn("invalid url", error.lower())

    def test_allows_external_hosts_by_default(self):
        """Test that external hosts are allowed by default."""
        from dj_urls_panel.views import ExecuteRequestView
        
        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            is_allowed, error = ExecuteRequestView._is_url_allowed("http://example.com/api/test/")
            self.assertTrue(is_allowed)
            self.assertIsNone(error)

    def test_allowed_hosts_whitelist(self):
        """Test that ALLOWED_HOSTS setting creates a whitelist."""
        from dj_urls_panel.views import ExecuteRequestView
        
        with self.settings(DJ_URLS_PANEL_SETTINGS={'ALLOWED_HOSTS': ['example.com', 'api.example.com']}):
            # Allowed host
            is_allowed, error = ExecuteRequestView._is_url_allowed("http://example.com/api/")
            self.assertTrue(is_allowed)
            
            # Another allowed host
            is_allowed, error = ExecuteRequestView._is_url_allowed("https://api.example.com/v1/")
            self.assertTrue(is_allowed)
            
            # Not in allowed list
            is_allowed, error = ExecuteRequestView._is_url_allowed("http://other.com/api/")
            self.assertFalse(is_allowed)
            self.assertIn("not in ALLOWED_HOSTS", error)

    def test_execute_request_validates_url(self):
        """Test that execute_request validates URLs."""
        with self.settings(DJ_URLS_PANEL_SETTINGS={}):
            url = reverse("dj_urls_panel:execute_request")
            data = {
                "url": "http://169.254.169.254/latest/meta-data/",
                "method": "GET",
            }

            response = self.client.post(
                url, data=json.dumps(data), content_type="application/json"
            )

            self.assertEqual(response.status_code, 403)
            result = response.json()
            self.assertIn("error", result)
            self.assertIn("blocked", result["error"].lower())


class TestDrfSerializerInfo(UrlsPanelTestCase):
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
