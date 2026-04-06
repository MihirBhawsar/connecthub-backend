"""
django-filter FilterSet classes for the posts app.
"""
import django_filters

from .models import Post


class PostFilter(django_filters.FilterSet):
    """
    Filter set for posts.

    Supports filtering by author username, media type, and date range.
    Used in PostViewSet via filter_backends = [DjangoFilterBackend].
    """

    author = django_filters.CharFilter(field_name="author__username", lookup_expr="iexact")
    media_type = django_filters.ChoiceFilter(choices=Post.MEDIA_TYPES)
    from_date = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    to_date = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    is_public = django_filters.BooleanFilter(field_name="is_public")

    class Meta:
        model = Post
        fields = ["author", "media_type", "from_date", "to_date", "is_public"]
