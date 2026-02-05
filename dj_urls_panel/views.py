from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib import admin
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import urllib.parse
import re

from .utils import UrlListInterface


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
    
    panel_settings = getattr(settings, 'DJ_URLS_PANEL_SETTINGS', {})
    allowed_hosts = panel_settings.get('ALLOWED_HOSTS', None)
    
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


@staff_member_required
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

    context = admin.site.each_context(request)
    context.update(
        {
            "title": "Dj Urls Panel",
            "urls": urls,
            "stats": stats,
            "grouped_urls": grouped_urls,
            "search_query": search_query,
            "namespace_filter": namespace_filter,
            "available_namespaces": available_namespaces,
            "has_root_urls": has_root_urls,
            "total_displayed": len(urls),
        }
    )
    return render(request, "admin/dj_urls_panel/index.html", context)


@staff_member_required
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
    panel_settings = getattr(settings, 'DJ_URLS_PANEL_SETTINGS', {})
    enable_testing = panel_settings.get('ENABLE_TESTING', True)

    context = admin.site.each_context(request)
    context.update(
        {
            "title": f"URL Detail: {url['pattern']}",
            "url": url,
            "short_name": short_name,
            "test_url": test_url,
            "base_url": base_url,
            "http_methods": url.get("http_methods", ["GET"]),
            "url_parameters": url.get("url_parameters", []),
            "serializer_info": url.get("serializer_info"),
            "serializer_fields_json": json.dumps(
                url.get("serializer_info", {}).get("fields", [])
                if url.get("serializer_info")
                else []
            ),
            "enable_testing": enable_testing,
        }
    )
    return render(request, "admin/dj_urls_panel/detail.html", context)


@staff_member_required
@require_http_methods(["POST"])
def execute_request(request):
    """
    Execute an HTTP request and return the response.
    This is a proxy endpoint for testing URLs.
    """
    from django.conf import settings as django_settings
    
    # Check if testing is enabled FIRST (before any other checks)
    panel_settings = getattr(django_settings, 'DJ_URLS_PANEL_SETTINGS', {})
    enable_testing = panel_settings.get('ENABLE_TESTING', True)
    
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
        is_allowed, error_message = _is_url_allowed(url)
        if not is_allowed:
            return JsonResponse({"error": error_message}, status=403)

        # Build authentication and cookies
        auth = None
        cookies = {}

        if auth_type == "session":
            # Forward the current user's session cookie
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            session_id = request.COOKIES.get(session_cookie_name)
            if session_id:
                cookies[session_cookie_name] = session_id

            # Forward CSRF cookie and add CSRF token for write operations
            csrf_cookie_name = django_settings.CSRF_COOKIE_NAME
            csrf_cookie_value = request.COOKIES.get(csrf_cookie_name)
            
            if method in ["POST", "PUT", "PATCH", "DELETE"]:
                # Get CSRF token from request
                csrf_token = request.META.get("CSRF_COOKIE")
                if not csrf_token:
                    csrf_token = csrf_cookie_value
                
                if csrf_token:
                    headers["X-CSRFToken"] = csrf_token
                    # Also forward the CSRF cookie itself
                    if csrf_cookie_value:
                        cookies[csrf_cookie_name] = csrf_cookie_value
                else:
                    # Try to obtain CSRF token by making a GET request first
                    try:
                        # Extract base URL for CSRF token fetch
                        from urllib.parse import urlparse
                        parsed_url = urlparse(url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        
                        # Make a GET request to get CSRF token
                        csrf_response = http_requests.get(
                            base_url,
                            cookies=cookies,
                            timeout=5,
                            allow_redirects=True
                        )
                        
                        # Extract CSRF token from response cookies
                        if csrf_cookie_name in csrf_response.cookies:
                            csrf_token = csrf_response.cookies[csrf_cookie_name]
                            cookies[csrf_cookie_name] = csrf_token
                            headers["X-CSRFToken"] = csrf_token
                    except Exception:
                        # If CSRF fetch fails, continue without it
                        pass
            else:
                # For read operations, still forward CSRF cookie if present
                if csrf_cookie_value:
                    cookies[csrf_cookie_name] = csrf_cookie_value
                    
        elif auth_type == "session_cookie" and auth_value:
            # Use the provided session ID
            session_cookie_name = django_settings.SESSION_COOKIE_NAME
            cookies[session_cookie_name] = auth_value

            # Forward CSRF cookie and add CSRF token for write operations
            csrf_cookie_name = django_settings.CSRF_COOKIE_NAME
            csrf_cookie_value = request.COOKIES.get(csrf_cookie_name)
            
            if method in ["POST", "PUT", "PATCH", "DELETE"]:
                csrf_token = request.META.get("CSRF_COOKIE")
                if not csrf_token:
                    csrf_token = csrf_cookie_value
                
                if csrf_token:
                    headers["X-CSRFToken"] = csrf_token
                    if csrf_cookie_value:
                        cookies[csrf_cookie_name] = csrf_cookie_value
                else:
                    # Try to obtain CSRF token by making a GET request first
                    try:
                        from urllib.parse import urlparse
                        parsed_url = urlparse(url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        
                        csrf_response = http_requests.get(
                            base_url,
                            cookies=cookies,
                            timeout=5,
                            allow_redirects=True
                        )
                        
                        if csrf_cookie_name in csrf_response.cookies:
                            csrf_token = csrf_response.cookies[csrf_cookie_name]
                            cookies[csrf_cookie_name] = csrf_token
                            headers["X-CSRFToken"] = csrf_token
                    except Exception:
                        pass
            else:
                # For read operations, still forward CSRF cookie if present
                if csrf_cookie_value:
                    cookies[csrf_cookie_name] = csrf_cookie_value
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

        # Prepare request kwargs
        request_kwargs = {
            "method": method,
            "url": url,
            "headers": headers,
            "timeout": timeout,
            "allow_redirects": True,
        }

        # Add cookies if any
        if cookies:
            request_kwargs["cookies"] = cookies

        # Add body for appropriate methods
        if body and method in ["POST", "PUT", "PATCH"]:
            # Try to parse as JSON
            try:
                json.loads(body)
                request_kwargs["data"] = body
                if "Content-Type" not in headers:
                    headers["Content-Type"] = "application/json"
            except json.JSONDecodeError:
                request_kwargs["data"] = body

        if auth:
            request_kwargs["auth"] = auth

        # Execute the request
        response = http_requests.request(**request_kwargs)

        # Try to parse response as JSON
        try:
            response_body = response.json()
            is_json = True
        except (json.JSONDecodeError, ValueError):
            response_body = response.text
            is_json = False

        # Build response headers dict
        response_headers = dict(response.headers)

        return JsonResponse(
            {
                "status_code": response.status_code,
                "status_text": response.reason,
                "headers": response_headers,
                "body": response_body,
                "is_json": is_json,
                "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
                "url": response.url,  # Final URL after redirects
            }
        )

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
