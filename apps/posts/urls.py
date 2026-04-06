"""
URL configuration for the posts app.
Mounted at /api/v1/ from config/urls.py.
"""
from django.urls import path

from . import views

app_name = "posts"

urlpatterns = [
    # Feed
    path("posts/", views.FeedView.as_view(), name="feed"),
    # Post CRUD
    path("posts/all/", views.PostListCreateView.as_view(), name="post-list"),
    path("posts/explore/", views.ExploreView.as_view(), name="explore"),
    path("posts/search/", views.PostSearchView.as_view(), name="search"),
    path("posts/hashtag/<str:name>/", views.HashtagFeedView.as_view(), name="hashtag-feed"),
    path("posts/<int:pk>/", views.PostDetailView.as_view(), name="post-detail"),
    path("posts/<int:pk>/like/", views.LikeToggleView.as_view(), name="like-toggle"),
    path("posts/<int:pk>/likes/", views.LikesListView.as_view(), name="like-list"),
    path("posts/<int:pk>/comments/", views.CommentListCreateView.as_view(), name="comment-list"),
    path("posts/comments/<int:pk>/", views.CommentDeleteView.as_view(), name="comment-delete"),
    # Stories
    path("stories/", views.StoryFeedView.as_view(), name="story-feed"),
    path("stories/create/", views.StoryCreateView.as_view(), name="story-create"),
    path("stories/<int:pk>/", views.StoryDeleteView.as_view(), name="story-delete"),
]
