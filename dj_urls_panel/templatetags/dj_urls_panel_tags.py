from django import template

register = template.Library()

# Stable colour per HTTP method, using the built-in dcr-badge variants so no
# panel-specific CSS is required.
_METHOD_VARIANTS = {
    "GET": "info",
    "POST": "success",
    "PUT": "warning",
    "PATCH": "purple",
    "DELETE": "danger",
    "HEAD": "indigo",
    "OPTIONS": "muted",
}


@register.filter
def http_method_badge_variant(method: str) -> str:
    """
    Map an HTTP method to a stable badge CSS class.

    Falls back to the plain (unstyled) badge for unrecognized methods.
    """
    variant = _METHOD_VARIANTS.get((method or "").upper())
    return f"dcr-badge dcr-badge--{variant}" if variant else "dcr-badge"
