"""
URL configuration for the notifications app.
Mounted at /api/v1/notifications/ from config/urls.py.
"""
from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("read-all/", views.MarkAllReadView.as_view(), name="read-all"),
    path("unread-count/", views.UnreadCountView.as_view(), name="unread-count"),
    path("<int:pk>/read/", views.MarkSingleReadView.as_view(), name="mark-read"),
]
