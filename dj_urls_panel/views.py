from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.contrib import admin

from .utils import UrlListInterface


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
