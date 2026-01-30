from django.db import models
from django.contrib.auth.models import User


class Article(models.Model):
    """Example Article model for API demonstration."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Comment(models.Model):
    """Example Comment model for API demonstration."""

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.article.title}"


class Tag(models.Model):
    """Example Tag model for API demonstration."""

    name = models.CharField(max_length=50, unique=True)
    articles = models.ManyToManyField(Article, related_name="tags", blank=True)

    def __str__(self):
        return self.name
