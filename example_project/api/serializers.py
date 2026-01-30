from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Article, Comment, Tag


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = ["id"]


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comment model."""

    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "article", "author", "text", "created_at"]
        read_only_fields = ["id", "created_at"]


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model."""

    class Meta:
        model = Tag
        fields = ["id", "name"]
        read_only_fields = ["id"]


class ArticleSerializer(serializers.ModelSerializer):
    """Serializer for Article model."""

    author = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(source="comments.count", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "content",
            "author",
            "created_at",
            "updated_at",
            "published",
            "comments",
            "tags",
            "comment_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ArticleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Article list view."""

    author = serializers.StringRelatedField()
    comment_count = serializers.IntegerField(source="comments.count", read_only=True)
    tag_count = serializers.IntegerField(source="tags.count", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id",
            "title",
            "author",
            "created_at",
            "published",
            "comment_count",
            "tag_count",
        ]
        read_only_fields = ["id", "created_at"]
