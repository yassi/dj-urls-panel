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
            # Check if it's a DRF ViewSet with actions (most specific)
            if hasattr(callback, 'actions') and callback.actions:
                # Actions is a dict mapping HTTP methods to ViewSet actions
                # e.g., {'get': 'list', 'post': 'create'} or {'get': 'retrieve', 'put': 'update', ...}
                actions = callback.actions
                
                # Map the actions back to HTTP methods
                for http_method in actions.keys():
                    method_upper = http_method.upper()
                    if method_upper in methods:
                        allowed_methods.append(method_upper)
                
                # Always include HEAD and OPTIONS for DRF views
                if 'GET' in allowed_methods:
                    if 'HEAD' not in allowed_methods:
                        allowed_methods.append('HEAD')
                if 'OPTIONS' not in allowed_methods:
                    allowed_methods.append('OPTIONS')
                
                return sorted(allowed_methods, key=lambda x: methods.index(x))
            
            # Check if view has http_method_names configured
            if hasattr(view_class, 'http_method_names'):
                configured_method_names = [m.lower() for m in view_class.http_method_names]
                
                # For each configured method, verify it's actually implemented
                for method in methods:
                    method_lower = method.lower()
                    
                    # Skip if not in configured methods
                    if method_lower not in configured_method_names:
                        continue
                    
                    # Check if the method exists on the view class
                    if hasattr(view_class, method_lower):
                        allowed_methods.append(method)
                
                if allowed_methods:
                    return allowed_methods
            
            # Fallback: Check for any implemented methods
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
    
    Supports both Django path-style (<type:name>) and regex-style ((?P<name>pattern)) parameters.
    
    Returns a list of parameter dictionaries with name and type info.
    """
    import re
    
    parameters = []
    seen_names = set()  # Track parameter names to avoid duplicates
    
    # FIRST: Match regex-style named groups: (?P<name>pattern)
    # We do this first because path patterns can match the <name> inside (?P<name>...)
    regex_param_pattern = r'\(\?P<(\w+)>[^)]+\)'
    
    for match in re.finditer(regex_param_pattern, pattern):
        param_name = match.group(1)
        
        if param_name not in seen_names:
            seen_names.add(param_name)
            
            parameters.append({
                'name': param_name,
                'type': 'regex',  # Indicate this is a regex parameter
                'in': 'path',
                'required': True,
            })
    
    # SECOND: Match Django's path converters: <type:name> or <name>
    # Only match if not preceded by "?P" to avoid matching inside regex named groups
    path_param_pattern = r'(?<!\?P)<(?:(\w+):)?(\w+)>'
    
    for match in re.finditer(path_param_pattern, pattern):
        param_type = match.group(1) or 'str'
        param_name = match.group(2)
        
        if param_name not in seen_names:
            seen_names.add(param_name)
            
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
        self._load_settings()

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
        
        # Apply URL exclusion filters from settings
        return self._filter_excluded_urls(self._url_patterns)

    def _load_settings(self):
        """
        Load DJ_URLS_PANEL_SETTINGS from Django settings.
        
        Sets default values if setting is not configured.
        """
        import re
        
        panel_settings = getattr(settings, 'DJ_URLS_PANEL_SETTINGS', {})
        
        # Get EXCLUDE_URLS patterns (can be strings or compiled regex patterns)
        exclude_patterns = panel_settings.get('EXCLUDE_URLS', [])
        
        # Compile regex patterns
        self.exclude_patterns = []
        for pattern in exclude_patterns:
            if isinstance(pattern, str):
                try:
                    self.exclude_patterns.append(re.compile(pattern))
                except re.error:
                    # Skip invalid regex patterns
                    pass
            elif hasattr(pattern, 'match'):
                # Already a compiled regex
                self.exclude_patterns.append(pattern)

    def _filter_excluded_urls(self, url_patterns):
        """
        Filter out URLs that match exclusion patterns.
        
        Args:
            url_patterns: List of URL pattern dictionaries
            
        Returns:
            Filtered list of URL patterns
        """
        if not self.exclude_patterns:
            return url_patterns
        
        filtered = []
        for url in url_patterns:
            pattern = url['pattern']
            # Remove leading slash for matching
            pattern_to_match = pattern.lstrip('/')
            
            # Check if pattern matches any exclusion pattern
            excluded = False
            for exclude_pattern in self.exclude_patterns:
                if exclude_pattern.match(pattern_to_match):
                    excluded = True
                    break
            
            if not excluded:
                filtered.append(url)
        
        return filtered

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

                # Get the pattern prefix and strip regex anchors before concatenation
                # This prevents issues with DRF routers that use regex patterns with ^ and $
                pattern_str = str(pattern.pattern)
                pattern_str = self._strip_regex_anchors(pattern_str)
                new_prefix = prefix + pattern_str

                # Recursively extract patterns from included URLconf
                url_list.extend(
                    self._extract_patterns(
                        pattern.url_patterns, namespace=new_namespace, prefix=new_prefix
                    )
                )

            elif isinstance(pattern, URLPattern):
                # This is an actual URL pattern
                # Strip regex anchors from this component before concatenating with prefix
                # This ensures patterns like "^users/$" become "users/" before being
                # combined with a prefix like "api/" to produce "/api/users/" not "/api/^users/$"
                pattern_str = str(pattern.pattern)
                pattern_str = self._strip_regex_anchors(pattern_str)
                full_pattern = prefix + pattern_str

                # Clean up the pattern for display (ensure leading slash)
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

    def _strip_regex_anchors(self, pattern_str):
        """
        Strip regex anchors (^ and $) from a pattern string component.
        
        This is necessary because Django REST Framework routers and other regex-based
        patterns may include ^ and $ anchors. When these patterns are included with
        a prefix (e.g., path("api/", include(router.urls))), we need to strip the
        anchors from each component BEFORE concatenation to avoid malformed patterns
        like "/api/^users/" instead of "/api/users/".
        
        Args:
            pattern_str: Raw pattern string component
            
        Returns:
            Pattern string with regex anchors removed
        """
        # Strip leading ^ and trailing $ from this pattern component
        # These are regex anchors that should not appear in the middle of concatenated patterns
        pattern_str = pattern_str.lstrip("^").rstrip("$")
        return pattern_str

    def _clean_pattern(self, pattern):
        """
        Clean up a URL pattern for display.

        Args:
            pattern: Raw pattern string (may already have components concatenated)

        Returns:
            Cleaned pattern string with proper leading slash
        """
        # Ensure it starts with /
        if not pattern.startswith("/"):
            pattern = "/" + pattern

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
            # DRF ViewSets may store the class in different attributes
            if hasattr(callback, "view_class"):
                view_class_obj = callback.view_class
                view_class = callback.view_class.__name__
                if hasattr(callback.view_class, "__module__"):
                    view_class = f"{callback.view_class.__module__}.{view_class}"
            elif hasattr(callback, "cls"):
                # Some DRF views use 'cls' instead of 'view_class'
                view_class_obj = callback.cls
                view_class = callback.cls.__name__
                if hasattr(callback.cls, "__module__"):
                    view_class = f"{callback.cls.__module__}.{view_class}"

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
