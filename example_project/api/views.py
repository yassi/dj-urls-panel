from rest_framework import viewsets, generics, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from .models import Article, Comment, Tag
from .serializers import (
    ArticleSerializer,
    ArticleListSerializer,
    CommentSerializer,
    TagSerializer,
    UserSerializer,
)


class ArticleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Article CRUD operations.
    Provides list, create, retrieve, update, partial_update, and destroy actions.
    """

    queryset = Article.objects.all()
    serializer_class = ArticleSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return ArticleListSerializer
        return ArticleSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Custom action to publish an article."""
        article = self.get_object()
        article.published = True
        article.save()
        return Response({"status": "article published"})

    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        """Custom action to unpublish an article."""
        article = self.get_object()
        article.published = False
        article.save()
        return Response({"status": "article unpublished"})

    @action(detail=False, methods=["get"])
    def published(self, request):
        """Custom action to get only published articles."""
        published_articles = self.queryset.filter(published=True)
        serializer = self.get_serializer(published_articles, many=True)
        return Response(serializer.data)


class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Comment CRUD operations.
    """

    queryset = Comment.objects.all()
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Tag CRUD operations.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for User model.
    Only provides list and retrieve actions.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer


# ===== Generic API Views =====


class ArticleListCreateView(generics.ListCreateAPIView):
    """
    Generic view for listing and creating articles.
    Alternative to using ViewSets.
    """

    queryset = Article.objects.all()
    serializer_class = ArticleListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Generic view for retrieving, updating, and deleting a single article.
    """

    queryset = Article.objects.all()
    serializer_class = ArticleSerializer


class PublishedArticlesView(generics.ListAPIView):
    """
    List only published articles.
    """

    queryset = Article.objects.filter(published=True)
    serializer_class = ArticleListSerializer


# ===== APIView Class-based Views =====


class ArticleStatsView(APIView):
    """
    Custom APIView to get article statistics.
    """

    def get(self, request):
        """Get statistics about articles."""
        total_articles = Article.objects.count()
        published_articles = Article.objects.filter(published=True).count()
        total_comments = Comment.objects.count()
        total_tags = Tag.objects.count()

        return Response(
            {
                "total_articles": total_articles,
                "published_articles": published_articles,
                "unpublished_articles": total_articles - published_articles,
                "total_comments": total_comments,
                "total_tags": total_tags,
            }
        )


class HealthCheckView(APIView):
    """
    Simple health check endpoint.
    """

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Return API health status."""
        return Response({"status": "ok", "api": "running"})


# ===== Function-based API Views =====


@api_view(["GET"])
def api_root(request):
    """
    API root endpoint providing information about available endpoints.
    """
    return Response(
        {
            "message": "Welcome to the Example API",
            "version": "1.0.0",
            "endpoints": {
                "articles": "/api/articles/",
                "comments": "/api/comments/",
                "tags": "/api/tags/",
                "users": "/api/users/",
                "stats": "/api/stats/",
                "health": "/api/health/",
            },
        }
    )


@api_view(["GET", "POST"])
def article_list(request):
    """
    Function-based view to list all articles or create a new one.
    """
    if request.method == "GET":
        articles = Article.objects.all()
        serializer = ArticleListSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == "POST":
        serializer = ArticleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def article_search(request):
    """
    Search articles by title or content.
    """
    query = request.query_params.get("q", "")
    if not query:
        return Response({"error": "Query parameter 'q' is required"}, status=400)

    articles = Article.objects.filter(title__icontains=query) | Article.objects.filter(
        content__icontains=query
    )
    serializer = ArticleListSerializer(articles, many=True)
    return Response(serializer.data)
