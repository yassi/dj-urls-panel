from django.db import models


class CeleryPanelPlaceholder(models.Model):
    """
    This is a fake model used to create an entry in the admin panel for dj_urls_panel.
    When we register this app with the admin site, it is configured to simply load
    the panel templates.
    """

    class Meta:
        managed = False
        verbose_name = "Dj Urls Panel"
        verbose_name_plural = "Dj Urls Panel"
