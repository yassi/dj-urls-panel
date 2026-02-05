from django.urls import path
from . import views

app_name = "dj_urls_panel"

urlpatterns = [
    path("", views.index, name="index"),
    path("detail/<path:pattern>/", views.url_detail, name="url_detail"),
    path("api/execute/", views.execute_request, name="execute_request"),
]
