from django.urls import URLPattern, URLResolver, get_resolver
from django.conf import settings


def get_drf_serializer_info(view_class):
    """
    Extract serializer information from a DRF view class.
    
    Returns a dictionary with serializer details or None if not a DRF view.
    """
    if view_class is None:
        return None
    
    try:
        # Check if it's a DRF view by looking for serializer_class
        serializer_class = getattr(view_class, 'serializer_class', None)
        
        if serializer_class is None:
            # Try to get it from get_serializer_class method
            if hasattr(view_class, 'get_serializer_class'):
                # We can't call it without an instance, but we can note it exists
                return {
                    'has_serializer': True,
                    'serializer_class': None,
                    'serializer_name': 'Dynamic (via get_serializer_class)',
                    'fields': [],
                    'is_dynamic': True,
                }
            return None
        
        # Get serializer fields
        fields_info = []
        try:
            # Create instance to get fields
            serializer_instance = serializer_class()
            fields = serializer_instance.fields
            
            for field_name, field in fields.items():
                field_type = type(field).__name__
                required = getattr(field, 'required', False)
                read_only = getattr(field, 'read_only', False)
                write_only = getattr(field, 'write_only', False)
                help_text = getattr(field, 'help_text', '') or ''
                
                # Get choices if available
                choices = None
                if hasattr(field, 'choices') and field.choices:
                    choices = list(field.choices.keys()) if isinstance(field.choices, dict) else list(field.choices)
                
                fields_info.append({
                    'name': field_name,
                    'type': field_type,
                    'required': required,
                    'read_only': read_only,
                    'write_only': write_only,
                    'help_text': str(help_text),
                    'choices': choices,
                })
        except Exception:
            # If we can't instantiate, just get basic info
            pass
        
        return {
            'has_serializer': True,
            'serializer_class': f"{serializer_class.__module__}.{serializer_class.__name__}",
            'serializer_name': serializer_class.__name__,
            'fields': fields_info,
            'is_dynamic': False,
        }
    except Exception:
        return None


def get_view_http_methods(callback):
    """
    Extract allowed HTTP methods from a view.
    
    Returns a list of HTTP methods the view supports.
    """
    methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
    allowed_methods = []
    
    if callback is None:
        return ['GET']
    
    try:
        # Check for DRF ViewSet or APIView
        view_class = getattr(callback, 'view_class', None) or getattr(callback, 'cls', None)
        
        if view_class:
            # Check for http_method_names attribute
            if hasattr(view_class, 'http_method_names'):
                return [m.upper() for m in view_class.http_method_names if m.upper() in methods]
            
            # Check for action methods (DRF ViewSets)
            for method in methods:
                method_lower = method.lower()
                if hasattr(view_class, method_lower):
                    allowed_methods.append(method)
            
            if allowed_methods:
                return allowed_methods
        
        # For function-based views, check if they have http_method_names or decorators
        if hasattr(callback, 'http_method_names'):
            return [m.upper() for m in callback.http_method_names if m.upper() in methods]
        
        # Default to common methods
        return ['GET', 'POST']
    except Exception:
        return ['GET', 'POST']


def extract_url_parameters(pattern):
    """
    Extract URL parameters from a URL pattern.
    
    Returns a list of parameter dictionaries with name and type info.
    """
    import re
    
    parameters = []
    
    # Match Django's path converters: <type:name> or <name>
    path_param_pattern = r'<(?:(\w+):)?(\w+)>'
    
    for match in re.finditer(path_param_pattern, pattern):
        param_type = match.group(1) or 'str'
        param_name = match.group(2)
        
        # Map Django path converters to more descriptive types
        type_mapping = {
            'int': 'integer',
            'str': 'string',
            'slug': 'slug',
            'uuid': 'UUID',
            'path': 'path',
        }
        
        parameters.append({
            'name': param_name,
            'type': type_mapping.get(param_type, param_type),
            'in': 'path',
            'required': True,
        })
    
    return parameters


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
                        "serializer_info": view_info.get("serializer_info"),
                        "http_methods": view_info.get("http_methods", ["GET"]),
                        "url_parameters": view_info.get("url_parameters", []),
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
            Dictionary with view_name, view_class, serializer_info, and http_methods
        """
        callback = pattern.callback
        view_name = None
        view_class = None
        view_class_obj = None

        if callback:
            # Get the module and name
            if hasattr(callback, "__name__"):
                view_name = callback.__name__

            if hasattr(callback, "__module__"):
                module = callback.__module__
                view_name = f"{module}.{view_name}" if view_name else module

            # Check if it's a class-based view
            if hasattr(callback, "view_class"):
                view_class_obj = callback.view_class
                view_class = callback.view_class.__name__
                if hasattr(callback.view_class, "__module__"):
                    view_class = f"{callback.view_class.__module__}.{view_class}"

        # Get DRF serializer info
        serializer_info = get_drf_serializer_info(view_class_obj)
        
        # Get HTTP methods
        http_methods = get_view_http_methods(callback)
        
        # Get URL parameters
        url_params = extract_url_parameters(str(pattern.pattern))

        return {
            "view_name": view_name or "Unknown",
            "view_class": view_class,
            "serializer_info": serializer_info,
            "http_methods": http_methods,
            "url_parameters": url_params,
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

    def get_url_by_pattern(self, pattern):
        """
        Get a specific URL by its pattern.

        Args:
            pattern: URL pattern to search for

        Returns:
            URL dictionary or None if not found
        """
        urls = self.get_url_list()
        for url in urls:
            if url["pattern"] == pattern:
                return url
        return None
