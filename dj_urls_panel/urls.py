from django.urls import path
from . import views

app_name = "dj_urls_panel"

urlpatterns = [
    path("", views.index, name="index"),
]
