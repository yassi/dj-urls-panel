from dj_control_room_base.core import PanelConfig

panel_config = PanelConfig(
    settings_key="DJ_URLS_PANEL_SETTINGS",
    defaults={
        "URL_CONFIG": None,
        "EXCLUDE_URLS": [],
        "ENABLE_TESTING": True,
        "ALLOWED_HOSTS": None,
    },
)
