from dj_control_room_base.core import PanelPlaceholderModel


class UrlsPanelPlaceholder(PanelPlaceholderModel):
    """
    This is a fake model used to create an entry in the admin panel for dj_urls_panel.
    When we register this app with the admin site, it is configured to simply load
    the panel templates.
    """

    class Meta(PanelPlaceholderModel.Meta):
        verbose_name = "Dj Urls Panel"
        verbose_name_plural = "Dj Urls Panel"
