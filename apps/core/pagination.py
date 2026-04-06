"""
Pagination classes for ConnectHub.

Two strategies:
- FeedCursorPagination  : cursor-based for the home feed (avoids duplicates on new inserts)
- StandardPagePagination: page-number for follower/following lists and other collections
"""
from rest_framework.pagination import CursorPagination, PageNumberPagination


class FeedCursorPagination(CursorPagination):
    """
    Cursor-based pagination for the home feed.

    Using cursor pagination instead of page numbers prevents duplicate items
    from appearing when new posts are inserted between page fetches.
    """

    page_size = 20
    ordering = "-created_at"
    cursor_query_param = "cursor"
    page_size_query_param = "page_size"
    max_page_size = 50


class StandardPagePagination(PageNumberPagination):
    """
    Standard page-number pagination for lists like followers and following.

    Simple to implement and works well for datasets that don't change rapidly.
    """

    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100


class NotificationPagination(PageNumberPagination):
    """Pagination for the notification list endpoint."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50
