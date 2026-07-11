from django.contrib import admin
from dj_control_room_base.core import BasePanelAdmin

from .conf import panel_config
from .models import UrlsPanelPlaceholder


@admin.register(UrlsPanelPlaceholder)
class UrlsPanelPlaceholderAdmin(BasePanelAdmin):
    redirect_url_name = "dj_urls_panel:index"
    panel_config = panel_config
