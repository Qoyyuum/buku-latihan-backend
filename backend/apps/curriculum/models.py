from typing import Any

from django.db import models
from django.utils.text import slugify


class Subject(models.Model):
    """Top-level grouping — e.g. Mathematics, Bahasa Melayu, Physics."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(**kwargs)


class Topic(models.Model):
    """Optional finer grouping inside a subject — e.g. Algebra, Fractions."""

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="topics",
    )
    name = models.CharField(max_length=120)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["subject", "order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "name"],
                name="unique_topic_per_subject",
            )
        ]

    def __str__(self) -> str:
        return f"{self.subject} / {self.name}"
