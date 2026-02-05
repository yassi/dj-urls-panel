from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for ViewSets
router = DefaultRouter()
router.register(r"articles", views.ArticleViewSet, basename="article")
router.register(r"comments", views.CommentViewSet, basename="comment")
router.register(r"tags", views.TagViewSet, basename="tag")
router.register(r"users", views.UserViewSet, basename="user")

app_name = "api"

urlpatterns = [
    # Router URLs (includes all ViewSet endpoints)
    path("router/", include(router.urls)),
    # Generic API Views
    path(
        "generic/articles/",
        views.ArticleListCreateView.as_view(),
        name="generic-article-list",
    ),
    path(
        "generic/articles/<int:pk>/",
        views.ArticleDetailView.as_view(),
        name="generic-article-detail",
    ),
    path(
        "generic/published/",
        views.PublishedArticlesView.as_view(),
        name="generic-published",
    ),
    # Custom APIViews
    path("stats/", views.ArticleStatsView.as_view(), name="stats"),
    path("health/", views.HealthCheckView.as_view(), name="health"),
    # Function-based views
    path("func/articles/", views.article_list, name="func-article-list"),
    path("func/search/", views.article_search, name="func-article-search"),
]
