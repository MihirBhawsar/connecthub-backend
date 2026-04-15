"""
Root URL configuration for ConnectHub.

All API routes are versioned under /api/v1/.
Swagger and ReDoc are served at /api/docs/ and /api/redoc/.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.conf.urls.static import static

from apps.core.views import HealthCheckView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Health check — public liveness probe
    path("api/v1/health/", HealthCheckView.as_view(), name="health-check"),

    # Users (auth + profile) — single namespace "users"
    path("api/v1/", include("apps.users.urls", namespace="users")),

    # Posts, stories, search — namespace "posts"
    path("api/v1/", include("apps.posts.urls", namespace="posts")),

    # Notifications — namespace "notifications"
    path("api/v1/notifications/", include("apps.notifications.urls", namespace="notifications")),

    # API docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
    
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
