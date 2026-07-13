from django.conf import settings as django_settings
from django.shortcuts import render
from django.http import Http404, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
import json
import urllib.parse
import re

from .conf import panel_config
from .utils import UrlListInterface


@panel_config.permission_required("index")
def index(request):
    """
    Display panel dashboard with URL list.
    """
    # Get URL collection interface
    url_interface = UrlListInterface()

    # Get search query and namespace filter
    search_query = request.GET.get("q", "").strip()
    namespace_filter = request.GET.get("namespace", "").strip()

    # Get all URLs first
    urls = url_interface.get_url_list()

    # Apply search filter
    if search_query:
        urls = [
            url
            for url in urls
            if (
                search_query.lower() in url["pattern"].lower()
                or (url["name"] and search_query.lower() in url["name"].lower())
                or search_query.lower() in url["view"].lower()
            )
        ]

    # Apply namespace filter
    if namespace_filter:
        if namespace_filter == "_root":
            # Filter for URLs with no namespace
            urls = [url for url in urls if not url["namespace"]]
        else:
            # Filter for specific namespace
            urls = [url for url in urls if url["namespace"] == namespace_filter]

    # Get statistics (always from full URL list)
    stats = url_interface.get_stats()

    # Get grouped URLs for navigation
    grouped_urls = url_interface.get_grouped_urls()

    # Get available namespaces for filter dropdown
    available_namespaces = sorted(
        set(
            url["namespace"] for url in url_interface.get_url_list() if url["namespace"]
        )
    )

    # Check if there are root-level URLs (no namespace)
    has_root_urls = any(not url["namespace"] for url in url_interface.get_url_list())

    context = panel_config.get_context(
        request,
        title="Dj Urls Panel",
        urls=urls,
        stats=stats,
        grouped_urls=grouped_urls,
        search_query=search_query,
        namespace_filter=namespace_filter,
        available_namespaces=available_namespaces,
        has_root_urls=has_root_urls,
        total_displayed=len(urls),
    )
    return render(request, "admin/dj_urls_panel/index.html", context)


@panel_config.permission_required("detail")
def url_detail(request, pattern):
    """
    Display detailed information about a specific URL.
    """
    # Get URL collection interface
    url_interface = UrlListInterface()

    # Decode the pattern from URL encoding
    decoded_pattern = urllib.parse.unquote(pattern)

    # Get the URL details
    url = url_interface.get_url_by_pattern(decoded_pattern)

    if not url:
        raise Http404("URL not found")

    # Extract short name (without namespace) if it has a namespace
    short_name = None
    if url["name"] and url["namespace"]:
        short_name = url["name"].split(":")[-1]

    # Build the base URL for testing
    base_url = request.build_absolute_uri("/").rstrip("/")
    test_url = base_url + url["pattern"]

    # Check if testing is enabled
    enable_testing = panel_config.get_settings("ENABLE_TESTING")

    context = panel_config.get_context(
        request,
        title=f"URL Detail: {url['pattern']}",
        url=url,
        short_name=short_name,
        test_url=test_url,
        base_url=base_url,
        http_methods=url.get("http_methods", ["GET"]),
        url_parameters=url.get("url_parameters", []),
        serializer_info=url.get("serializer_info"),
        serializer_fields_json=json.dumps(
            url.get("serializer_info", {}).get("fields", [])
            if url.get("serializer_info")
            else []
        ),
        enable_testing=enable_testing,
    )
    return render(request, "admin/dj_urls_panel/detail.html", context)


@method_decorator(panel_config.permission_required("execute"), name="dispatch")
class ExecuteRequestView(View):
    """
    Proxy endpoint backing the URL testing interface: executes an HTTP
    request on behalf of the browser (to dodge CORS/CSRF friction in the
    admin UI) and returns the response as JSON.

    Implemented as a class so the auth/CSRF/body-building concerns can live
    as small, independently testable methods instead of one long function.
    Only POST is supported; any other method gets Django's standard 405.
    """

    http_method_names = ["post"]

    # Methods for which a CSRF token must be forwarded/obtained when
    # authenticating as the current Django session.
    CSRF_REQUIRED_METHODS = ("POST", "PUT", "PATCH", "DELETE")

    # Methods that may carry a request body.
    BODY_METHODS = ("POST", "PUT", "PATCH")

    def post(self, request):
        # Check if testing is enabled FIRST (before any other checks)
        enable_testing = panel_config.get_settings("ENABLE_TESTING")

        if not enable_testing:
            return JsonResponse(
                {
                    "error": "URL testing is disabled. Set ENABLE_TESTING=True in DJ_URLS_PANEL_SETTINGS to enable it."
                },
                status=403,
            )

        try:
            import requests as http_requests
        except ImportError:
            return JsonResponse(
                {
                    "error": "The 'requests' library is required for URL testing. Install it with: pip install requests"
                },
                status=500,
            )

        # Stashed for the duration of this request so helper methods (and
        # the CSRF-minting fallback in particular) can issue their own calls
        # through the same module.
        self.http_requests = http_requests

        try:
            data = json.loads(request.body)

            url = data.get("url", "")
            method = data.get("method", "GET").upper()
            headers = data.get("headers", {})
            body = data.get("body", "")
            auth_type = data.get("auth_type")
            auth_value = data.get("auth_value")
            timeout = data.get("timeout", 30)

            # Validate URL
            if not url:
                return JsonResponse({"error": "URL is required"}, status=400)

            # Validate URL against allowed hosts / SSRF protection
            is_allowed, error_message = self._is_url_allowed(url)
            if not is_allowed:
                return JsonResponse({"error": error_message}, status=403)

            auth, cookies = self._build_auth_and_cookies(
                request, url, method, headers, auth_type, auth_value
            )
            request_kwargs = self._build_request_kwargs(
                url, method, headers, body, timeout, auth, cookies
            )

            # Execute the request
            response = http_requests.request(**request_kwargs)

            return JsonResponse(self._format_response(response))

        except http_requests.exceptions.Timeout:
            return JsonResponse({"error": "Request timed out"}, status=408)
        except http_requests.exceptions.ConnectionError as e:
            return JsonResponse({"error": f"Connection error: {str(e)}"}, status=502)
        except http_requests.exceptions.RequestException as e:
            return JsonResponse({"error": f"Request failed: {str(e)}"}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON in request body"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    @staticmethod
    def _is_url_allowed(url):
        """
        Validate if a URL is allowed for testing based on DJ_URLS_PANEL_SETTINGS.

        Blocks dangerous internal targets by default (cloud metadata, private IPs, localhost).
        Allows only hosts specified in ALLOWED_HOSTS if configured.

        Args:
            url: The URL string to validate

        Returns:
            tuple: (is_allowed: bool, error_message: str or None)
        """
        from urllib.parse import urlparse

        allowed_hosts = panel_config.get_settings('ALLOWED_HOSTS')

        try:
            parsed = urlparse(url)
            hostname = parsed.hostname

            if not hostname:
                return False, "Invalid URL: No hostname found"

            # If ALLOWED_HOSTS is configured, only allow those hosts
            if allowed_hosts is not None:
                if hostname not in allowed_hosts:
                    return False, f"Host '{hostname}' is not in ALLOWED_HOSTS"
                return True, None

            # Default blocklist for SSRF protection
            # Block localhost and private IP ranges
            blocked_patterns = [
                r'^localhost$',
                r'^127\.',  # Loopback
                r'^10\.',   # Private class A
                r'^172\.(1[6-9]|2[0-9]|3[01])\.',  # Private class B
                r'^192\.168\.',  # Private class C
                r'^169\.254\.',  # Link-local (includes cloud metadata)
                r'^::1$',  # IPv6 localhost
                r'^fe80:',  # IPv6 link-local
                r'^fc00:',  # IPv6 private
            ]

            for pattern in blocked_patterns:
                if re.match(pattern, hostname, re.IGNORECASE):
                    return False, f"Host '{hostname}' is blocked for security reasons (internal/private IP)"

            return True, None

        except Exception as e:
            return False, f"Invalid URL: {str(e)}"

    def _forward_csrf_token(self, request, url, method, headers, cookies):
        """
        Attach CSRF credentials to a session-authenticated proxied request.

        For write methods, ensures an ``X-CSRFToken`` header is present, falling
        back to a best-effort GET against the target host to mint one if the
        caller's own request didn't carry a usable token. For read methods,
        simply forwards the CSRF cookie (if any) so the target can validate it
        on subsequent writes.

        Mutates ``headers`` and ``cookies`` in place.
        """
        csrf_cookie_name = django_settings.CSRF_COOKIE_NAME
        csrf_cookie_value = request.COOKIES.get(csrf_cookie_name)

        if method not in self.CSRF_REQUIRED_METHODS:
            if csrf_cookie_value:
                cookies[csrf_cookie_name] = csrf_cookie_value
            return

        csrf_token = request.META.get("CSRF_COOKIE") or csrf_cookie_value

        if csrf_token:
            headers["X-CSRFToken"] = csrf_token
            if csrf_cookie_value:
                cookies[csrf_cookie_name] = csrf_cookie_value
            return

        # No token available locally - try to mint one by hitting the target
        # host directly. Best-effort only: silently continue without a token if
        # this fails, since the downstream request may not even require one.
        try:
            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            csrf_response = self.http_requests.get(
                base_url, cookies=cookies, timeout=5, allow_redirects=True
            )

            if csrf_cookie_name in csrf_response.cookies:
                csrf_token = csrf_response.cookies[csrf_cookie_name]
                cookies[csrf_cookie_name] = csrf_token
                headers["X-CSRFToken"] = csrf_token
        except Exception:
            pass

    def _build_auth_and_cookies(self, request, url, method, headers, auth_type, auth_value):
        """
        Resolve the ``auth`` tuple and ``cookies`` dict for a proxied request,
        mutating ``headers`` in place with any Authorization/CSRF headers implied
        by ``auth_type``.

        Returns:
            tuple: (auth, cookies) where ``auth`` is a (username, password) tuple
            or None, and ``cookies`` is a dict (possibly empty).
        """
        auth = None
        cookies = {}

        if auth_type == "session":
            # Forward the current user's session cookie.
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            session_id = request.COOKIES.get(session_cookie_name)
            if session_id:
                cookies[session_cookie_name] = session_id
            self._forward_csrf_token(request, url, method, headers, cookies)

        elif auth_type == "session_cookie" and auth_value:
            # Use the explicitly provided session ID.
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            cookies[session_cookie_name] = auth_value
            self._forward_csrf_token(request, url, method, headers, cookies)

        elif auth_type and auth_value:
            if auth_type == "basic":
                # Expect auth_value as "username:password"
                if ":" in auth_value:
                    username, password = auth_value.split(":", 1)
                    auth = (username, password)
            elif auth_type == "bearer":
                headers["Authorization"] = f"Bearer {auth_value}"
            elif auth_type == "token":
                headers["Authorization"] = f"Token {auth_value}"

        return auth, cookies

    @staticmethod
    def _build_request_kwargs(url, method, headers, body, timeout, auth, cookies):
        """
        Assemble the kwargs dict passed to ``requests.request()`` for the
        proxied call, including an optional JSON-aware body and auth/cookies.
        """
        request_kwargs = {
            "method": method,
            "url": url,
            "headers": headers,
            "timeout": timeout,
            "allow_redirects": True,
        }

        if cookies:
            request_kwargs["cookies"] = cookies

        if body and method in ExecuteRequestView.BODY_METHODS:
            try:
                json.loads(body)
                request_kwargs["data"] = body
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"
            except json.JSONDecodeError:
                request_kwargs["data"] = body

        if auth:
            request_kwargs["auth"] = auth

        return request_kwargs

    @staticmethod
    def _format_response(response):
        """
        Convert a ``requests.Response`` into the JSON-serializable dict returned
        to the front-end testing interface.
        """
        try:
            response_body = response.json()
            is_json = True
        except (json.JSONDecodeError, ValueError):
            response_body = response.text
            is_json = False

        return {
            "status_code": response.status_code,
            "status_text": response.reason,
            "headers": dict(response.headers),
            "body": response_body,
            "is_json": is_json,
            "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
            "url": response.url,  # Final URL after redirects
        }
