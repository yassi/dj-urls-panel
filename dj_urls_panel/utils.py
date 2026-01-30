from django.urls import URLPattern, URLResolver, get_resolver
from django.conf import settings


class UrlListInterface:
    """
    Interface for collecting and organizing URL patterns from Django's URLconf.
    """

    def __init__(self, urlconf=None):
        """
        Initialize the interface with a specific URLconf or use ROOT_URLCONF.

        Args:
            urlconf: String path to URLconf module (e.g., 'myproject.urls')
                    If None, uses settings.ROOT_URLCONF
        """
        self.urlconf = urlconf or settings.ROOT_URLCONF
        self.resolver = get_resolver(self.urlconf)
        self._url_patterns = []

    def get_url_list(self):
        """
        Get the complete list of URL patterns with metadata.

        Returns:
            List of dictionaries containing URL pattern information:
            [
                {
                    'pattern': '/admin/login/',
                    'name': 'admin:login',
                    'view': 'django.contrib.admin.sites.login',
                    'namespace': 'admin',
                    'app_name': None,
                },
                ...
            ]
        """
        if not self._url_patterns:
            self._url_patterns = self._extract_patterns(
                self.resolver.url_patterns, namespace="", prefix=""
            )
        return self._url_patterns

    def _extract_patterns(self, patterns, namespace="", prefix=""):
        """
        Recursively extract URL patterns from URLconf.

        Args:
            patterns: List of URLPattern or URLResolver objects
            namespace: Current namespace string
            prefix: Current URL prefix

        Returns:
            List of URL pattern dictionaries
        """
        url_list = []

        for pattern in patterns:
            if isinstance(pattern, URLResolver):
                # This is an included URLconf (e.g., include('app.urls'))
                new_namespace = namespace
                if pattern.namespace:
                    new_namespace = (
                        f"{namespace}:{pattern.namespace}"
                        if namespace
                        else pattern.namespace
                    )

                # Get the pattern prefix
                pattern_str = str(pattern.pattern)
                new_prefix = prefix + pattern_str

                # Recursively extract patterns from included URLconf
                url_list.extend(
                    self._extract_patterns(
                        pattern.url_patterns, namespace=new_namespace, prefix=new_prefix
                    )
                )

            elif isinstance(pattern, URLPattern):
                # This is an actual URL pattern
                pattern_str = str(pattern.pattern)
                full_pattern = prefix + pattern_str

                # Clean up the pattern for display
                full_pattern = self._clean_pattern(full_pattern)

                # Get view information
                view_info = self._get_view_info(pattern)

                # Build the full name with namespace
                full_name = None
                if pattern.name:
                    full_name = (
                        f"{namespace}:{pattern.name}" if namespace else pattern.name
                    )

                url_list.append(
                    {
                        "pattern": full_pattern,
                        "name": full_name,
                        "view": view_info["view_name"],
                        "view_class": view_info["view_class"],
                        "namespace": namespace or None,
                        "app_name": pattern.pattern.name
                        if hasattr(pattern.pattern, "name")
                        else None,
                    }
                )

        return url_list

    def _clean_pattern(self, pattern):
        """
        Clean up a URL pattern for display.

        Args:
            pattern: Raw pattern string

        Returns:
            Cleaned pattern string
        """
        # Remove leading ^
        pattern = pattern.lstrip("^")

        # Ensure it starts with /
        if not pattern.startswith("/"):
            pattern = "/" + pattern

        # Remove trailing $
        pattern = pattern.rstrip("$")

        return pattern

    def _get_view_info(self, pattern):
        """
        Extract view information from a URLPattern.

        Args:
            pattern: URLPattern object

        Returns:
            Dictionary with view_name and view_class
        """
        callback = pattern.callback
        view_name = None
        view_class = None

        if callback:
            # Get the module and name
            if hasattr(callback, "__name__"):
                view_name = callback.__name__

            if hasattr(callback, "__module__"):
                module = callback.__module__
                view_name = f"{module}.{view_name}" if view_name else module

            # Check if it's a class-based view
            if hasattr(callback, "view_class"):
                view_class = callback.view_class.__name__
                if hasattr(callback.view_class, "__module__"):
                    view_class = f"{callback.view_class.__module__}.{view_class}"

        return {
            "view_name": view_name or "Unknown",
            "view_class": view_class,
        }

    def get_grouped_urls(self):
        """
        Get URLs grouped by namespace.

        Returns:
            Dictionary with namespaces as keys and URL lists as values
        """
        urls = self.get_url_list()
        grouped = {}

        for url in urls:
            namespace = url["namespace"] or "_root"
            if namespace not in grouped:
                grouped[namespace] = []
            grouped[namespace].append(url)

        return grouped

    def search_urls(self, query):
        """
        Search URLs by pattern, name, or view.

        Args:
            query: Search query string

        Returns:
            Filtered list of URL dictionaries
        """
        urls = self.get_url_list()
        query_lower = query.lower()

        return [
            url
            for url in urls
            if (
                query_lower in url["pattern"].lower()
                or (url["name"] and query_lower in url["name"].lower())
                or query_lower in url["view"].lower()
            )
        ]

    def get_stats(self):
        """
        Get statistics about the URL configuration.

        Returns:
            Dictionary with URL statistics
        """
        urls = self.get_url_list()
        namespaces = set(url["namespace"] for url in urls if url["namespace"])
        named_urls = [url for url in urls if url["name"]]

        return {
            "total_urls": len(urls),
            "named_urls": len(named_urls),
            "namespaces": len(namespaces),
            "namespace_list": sorted(namespaces),
        }
