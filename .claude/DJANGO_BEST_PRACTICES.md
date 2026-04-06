# Django Best Practices — ConnectHub Code Standards
## Claude Code must follow every rule in this file without exception

---

## 🚫 Anti-Patterns — NEVER Write These

### Models
```python
# ❌ NEVER — ForeignKey without on_delete
author = ForeignKey(User)

# ✅ ALWAYS
author = ForeignKey(User, on_delete=CASCADE, related_name='posts')

# ❌ NEVER — No related_name (causes reverse accessor clashes)
user = ForeignKey(User, on_delete=CASCADE)

# ✅ ALWAYS — descriptive related_name
user = ForeignKey(User, on_delete=CASCADE, related_name='liked_posts')

# ❌ NEVER — CharField without max_length
title = CharField()

# ❌ NEVER — null=True on CharField/TextField (use blank=True only)
name = CharField(max_length=100, null=True)

# ✅ ALWAYS — blank=True for optional strings, never null=True
name = CharField(max_length=100, blank=True, default='')

# ❌ NEVER — No __str__ on model
class Post(Model):
    pass

# ✅ ALWAYS — meaningful __str__
def __str__(self):
    return f"Post({self.id}) by {self.author.username}"

# ❌ NEVER — No Meta class
class Post(Model):
    created_at = DateTimeField(auto_now_add=True)

# ✅ ALWAYS — ordering + verbose names + indexes
class Meta:
    ordering = ['-created_at']
    verbose_name = 'Post'
    verbose_name_plural = 'Posts'
    indexes = [
        models.Index(fields=['-created_at']),
        models.Index(fields=['author', '-created_at']),
    ]
```

### Views / ViewSets
```python
# ❌ NEVER — Raw queryset without select_related (N+1 queries)
def get_queryset(self):
    return Post.objects.all()

# ✅ ALWAYS — select_related for FK, prefetch_related for M2M
def get_queryset(self):
    return Post.objects.select_related('author').prefetch_related('hashtags', 'likes').order_by('-created_at')

# ❌ NEVER — No permission_classes
class PostViewSet(ModelViewSet):
    queryset = Post.objects.all()

# ✅ ALWAYS — explicit permissions
class PostViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]

# ❌ NEVER — Exposing all fields in serializer
class PostSerializer(ModelSerializer):
    class Meta:
        fields = '__all__'

# ✅ ALWAYS — explicit fields list
class PostSerializer(ModelSerializer):
    class Meta:
        fields = ['id', 'author', 'caption', 'media_file', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']

# ❌ NEVER — Business logic in views
class PostViewSet(ModelViewSet):
    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        # 50 lines of business logic here ← WRONG

# ✅ ALWAYS — Logic in model methods or service layer
class PostViewSet(ModelViewSet):
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        # Signal/task handles the rest
```

### Serializers
```python
# ❌ NEVER — No validation on user-supplied fields
class PostSerializer(ModelSerializer):
    pass

# ✅ ALWAYS — validate_ methods for field-level, validate for object-level
def validate_caption(self, value):
    if len(value) > 2200:
        raise serializers.ValidationError("Caption too long.")
    return value.strip()

# ❌ NEVER — Nested writes without explicit create/update
class PostSerializer(ModelSerializer):
    author = UserSerializer()  # will break on POST

# ✅ ALWAYS — Separate read/write serializers or SerializerMethodField
class PostSerializer(ModelSerializer):
    author = UserMinimalSerializer(read_only=True)
    author_id = PrimaryKeyRelatedField(write_only=True, queryset=User.objects.all(), source='author')
```

### URLs
```python
# ❌ NEVER — No API versioning
path('posts/', PostViewSet.as_view({'get': 'list'}))

# ✅ ALWAYS — versioned URLs
path('api/v1/', include('apps.posts.urls'))

# ❌ NEVER — Function-based URL registration for ViewSets
# ✅ ALWAYS — Router
router = DefaultRouter()
router.register('posts', PostViewSet, basename='post')
```

### Security
```python
# ❌ NEVER — Hardcoded secrets in settings
SECRET_KEY = 'django-insecure-abc123'
DATABASE_URL = 'postgres://user:pass@localhost/db'

# ✅ ALWAYS — django-environ
SECRET_KEY = env('DJANGO_SECRET_KEY')
DATABASE_URL = env.db('DATABASE_URL')

# ❌ NEVER — DEBUG=True in production settings file
# ✅ ALWAYS — DEBUG = env.bool('DEBUG', default=False) in production

# ❌ NEVER — ALLOWED_HOSTS = ['*']
# ✅ ALWAYS — ALLOWED_HOSTS = env.list('ALLOWED_HOSTS')
```

### Celery Tasks
```python
# ❌ NEVER — Task without bind=True and retry logic
@shared_task
def generate_thumbnail(post_id):
    post = Post.objects.get(id=post_id)  # can raise DoesNotExist

# ✅ ALWAYS — bound task with retry + safe DB access
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_thumbnail(self, post_id):
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return  # Post deleted before task ran — fine, just exit
    try:
        # do work
    except Exception as exc:
        raise self.retry(exc=exc)

# ❌ NEVER — Pass model instances to Celery tasks
generate_thumbnail.delay(post_instance)  # breaks serialization

# ✅ ALWAYS — Pass primary keys only
generate_thumbnail.delay(post.id)
```

### File Uploads
```python
# ❌ NEVER — No file type validation
def perform_create(self, serializer):
    serializer.save()

# ✅ ALWAYS — Validate MIME type by reading magic bytes, not just extension
def validate_media_file(self, value):
    import magic
    allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'video/mp4', 'audio/mpeg']
    file_type = magic.from_buffer(value.read(1024), mime=True)
    value.seek(0)
    if file_type not in allowed_types:
        raise serializers.ValidationError(f"Unsupported file type: {file_type}")
    return value

# ❌ NEVER — No file size limit
# ✅ ALWAYS — check content_length
MAX_SIZES = {'image': 10_000_000, 'video': 500_000_000, 'audio': 50_000_000}
if value.size > MAX_SIZES.get(media_type, 10_000_000):
    raise serializers.ValidationError("File too large.")
```

---

## ✅ Mandatory Patterns

### Every Model Must Have
```python
class MyModel(Model):
    created_at = DateTimeField(auto_now_add=True)   # always
    updated_at = DateTimeField(auto_now=True)        # if mutable

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['-created_at'])]

    def __str__(self):
        return f"{self.__class__.__name__}({self.pk})"
```

### Every ViewSet Must Have
```python
class MyViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    pagination_class = StandardPagePagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MyFilter
    search_fields = ['field1', 'field2']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return MyModel.objects.select_related(...).filter(...)
```

### Object-Level Permissions
```python
# apps/core/permissions.py
class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user

# Use on every update/delete endpoint:
# permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
```

### Custom Exception Handler
```python
# apps/core/exceptions.py
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            'error': True,
            'status_code': response.status_code,
            'message': response.data,
        }
    return response

# config/settings/base.py
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
}
```

### Consistent API Response Format
```python
# Every list endpoint returns:
{
    "count": 42,
    "next": "http://...",
    "previous": null,
    "results": [...]
}

# Every create/update returns the full serialized object
# Every delete returns 204 No Content
# Every error returns:
{
    "error": true,
    "status_code": 400,
    "message": {"field": ["error detail"]}
}
```

---

## 📐 Code Style Rules

- **Line length**: max 100 chars
- **Imports order**: stdlib → Django → DRF → third-party → local apps
- **No bare `except:`** — always catch specific exceptions
- **No print()** — use `import logging; logger = logging.getLogger(__name__)`
- **Docstrings**: every class and non-trivial method gets one
- **No magic numbers** — use named constants or settings
- **Type hints**: add to all function signatures
- **f-strings only** — never % formatting or .format()

---

## 🗂️ App Structure Rules

Each app must follow this exact layout:
```
apps/myapp/
├── __init__.py
├── admin.py          ← Register all models
├── apps.py           ← AppConfig with default_auto_field
├── models.py         ← Models only, no business logic
├── serializers.py    ← Serializers only
├── views.py          ← ViewSets only, thin — no business logic
├── urls.py           ← Router registration only
├── signals.py        ← Django signals (post_save, etc.)
├── tasks.py          ← Celery tasks only
├── permissions.py    ← Custom DRF permissions
├── filters.py        ← django-filter FilterSet classes
├── managers.py       ← Custom QuerySet/Manager (if needed)
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    ├── test_serializers.py
    └── test_tasks.py
```

---

## 🔍 Query Optimization Rules

1. **Always use `select_related`** for ForeignKey/OneToOne in list views
2. **Always use `prefetch_related`** for ManyToMany/reverse FK in list views
3. **Never query inside a loop** — use `in` lookups or batch queries
4. **Use `only()` or `defer()`** for large models when you don't need all fields
5. **Use `exists()` not `count() > 0`** for existence checks
6. **Use `update()` not save()** for bulk field updates
7. **Use `F()` expressions** for counter increments (atomic, no race condition)
   ```python
   # ❌ NEVER (race condition)
   post.likes_count += 1
   post.save()
   
   # ✅ ALWAYS (atomic)
   Post.objects.filter(id=post.id).update(likes_count=F('likes_count') + 1)
   ```
8. **Index every ForeignKey** that is used in filter/order operations
9. **Use `values_list('id', flat=True)`** when you only need IDs

---

## 🔐 Authentication Rules

- Every endpoint must explicitly declare `permission_classes` — no relying on global default for security-sensitive endpoints
- Unauthenticated users get `401 Unauthorized`, not `403 Forbidden`
- Use `IsAuthenticatedOrReadOnly` for public-read / auth-required-write
- JWT tokens must never be stored in localStorage on clients (document this in README)
- Password reset tokens expire in 1 hour
- Refresh token rotation must be enabled (already set in SIMPLE_JWT config)

---

## 📝 Admin Registration

Every model must be registered in `admin.py`:
```python
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'media_type', 'likes_count', 'created_at']
    list_filter = ['media_type', 'is_public', 'created_at']
    search_fields = ['author__username', 'caption']
    raw_id_fields = ['author']
    readonly_fields = ['created_at', 'updated_at', 'likes_count']
```

---

## 🌐 CORS and Security Headers

```python
# production.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True
```
