from dj_control_room_base.core import PanelPlugin


class UrlsPanel(PanelPlugin):
    name = "URLs Panel"
    description = "Inspect and search your project's URL patterns"
    icon = "link"
    icon_color = "info"
    features = [
        "Browse all registered URL patterns in one place",
        "Filter by namespace, name, or path fragment",
        "Inspect view functions and their source modules",
        "Identify unnamed or duplicate routes at a glance",
    ]

    def get_url_name(self):
        return "index"

    def get_config(self):
        from .conf import panel_config

        return panel_config
