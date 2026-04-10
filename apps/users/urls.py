"""
URL configuration for the users app.
All patterns are mounted at /api/v1/ from config/urls.py.
This single module keeps namespace="users" unified so reverse() works consistently.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = "users"

urlpatterns = [
    # ----------------------------------------------------------------
    # Auth endpoints  →  /api/v1/auth/*
    # ----------------------------------------------------------------
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("auth/password/change/", views.ChangePasswordView.as_view(), name="password_change"),

    # ----------------------------------------------------------------
    # User profile endpoints  →  /api/v1/users/*
    # ----------------------------------------------------------------
    path("users/me/", views.MeView.as_view(), name="me"),
    path("users/search/", views.UserSearchView.as_view(), name="search"),
    path("users/suggestions/", views.UserSuggestionsView.as_view(), name="suggestions"),
    path("users/<str:username>/follow/", views.FollowToggleView.as_view(), name="follow"),
    path("users/<str:username>/followers/", views.FollowersListView.as_view(), name="followers"),
    path("users/<str:username>/following/", views.FollowingListView.as_view(), name="following"),
    path("users/<str:username>/block/", views.BlockToggleView.as_view(), name="block"),
    path("users/<str:username>/", views.UserProfileView.as_view(), name="profile"),
]
