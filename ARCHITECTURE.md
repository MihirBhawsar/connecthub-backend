# ConnectHub — Architecture Decision Record

## 1. Why cursor-based pagination for the home feed

**Decision**: Use `CursorPagination` for `/api/v1/posts/` (home feed).

**Reason**: The home feed is ordered by `created_at DESC` and receives new
posts continuously. Page-number pagination (`?page=2`) is offset-based: if
10 new posts are inserted between a client fetching page 1 and page 2, the
client will see 10 duplicates on page 2 (items that were pushed down by the
new inserts). Cursor pagination encodes the position as an opaque pointer,
so each "next" request resumes exactly where the last left off — no duplicates,
no missed items.

---

## 2. Why denormalized counters on Post

**Decision**: `Post.likes_count` and `Post.comments_count` are integer fields
updated via atomic `F()` expressions instead of being derived via `COUNT()`.

**Reason**: On a hot post with 100k likes, `SELECT COUNT(*) FROM likes WHERE post_id=X`
requires a full index scan on every feed render. At 1000 concurrent users viewing
the feed, this is 1000 expensive COUNT queries per second. By storing denormalized
counters and updating them atomically in signals using
`Post.objects.filter(id=pk).update(likes_count=F('likes_count') + 1)`, the
counter read is a single indexed column lookup with no aggregation.
Race conditions are impossible because Django ORM translates `F()` to SQL `UPDATE ... SET likes_count = likes_count + 1`.

---

## 3. Why Redis for feed caching

**Decision**: Cache the ordered list of post IDs per user in Redis for 5 minutes.

**Reason**: A user with 500 followers generates a feed query that involves:
- A JOIN between `follows` and `posts` tables
- Filtering `is_public=True` and excluding blocked users
- Sorting by `created_at DESC`
- Returning the top 20 rows with author + hashtag prefetch

For a user with 5000 followers this query touches potentially millions of rows.
At scale, the database cannot sustain this per request. Redis holds the ordered
post ID list (serializable, lightweight) and returns it in <1ms. On cache miss,
the DB query runs once and the result is cached for the next 300 seconds.

Feed invalidation is triggered when a followed user publishes a new post (signal
calls `cache.delete_many` for all follower feed keys), keeping the cache fresh.

---

## 4. Why Celery for thumbnail generation

**Decision**: Thumbnail generation runs in a Celery worker, not inline in the
HTTP request handler.

**Reason**: Image processing with Pillow or video frame extraction with ffmpeg
can take 2–30 seconds depending on file size and format. If this ran synchronously
in the view's `perform_create`, the client would wait that entire duration for
a 201 response. Celery decouples the work: the view returns 201 immediately,
and the thumbnail appears on the post object within seconds (async). The task
uses `bind=True, max_retries=3` so transient failures (e.g., S3 timeout) are
automatically retried with exponential backoff.

---

## 5. Why Django Channels + Redis channel layer

**Decision**: Real-time notifications are pushed via WebSocket through Django
Channels backed by a Redis channel layer.

**Reason**: A polling approach (`GET /notifications/` every 5 seconds) generates
constant HTTP traffic even when there are no new notifications. WebSocket
maintains a persistent connection with near-zero overhead when idle. When a
like/follow/comment signal fires, it calls `channel_layer.group_send()` which
pushes the notification JSON directly to the connected consumer(s) in that user's
group. The Redis channel layer enables horizontal scaling: multiple Daphne
instances share the same Redis pub/sub bus, so a WebSocket connected to server A
receives events sent by server B.

---

## 6. Why S3 presigned URLs

**Decision**: All media files are stored on AWS S3 with `AWS_QUERYSTRING_AUTH=True`
and a 1-hour presigned URL expiry. Django never proxies media file downloads.

**Reason**: If Django served media files directly, every media request would
consume an application server thread, memory, and CPU — making the web tier
the bottleneck for what is fundamentally just file I/O. S3 presigned URLs let
clients download files directly from S3's global CDN infrastructure with no
load on the application servers. Setting `AWS_DEFAULT_ACL='private'` ensures
files are never publicly readable without a valid time-limited signature,
enforcing access control without requiring application-level gating per request.

---

## High-Level Architecture Diagram

```
Client (Web / Mobile)
        │
        │  HTTPS / WSS
        ▼
    Nginx (TLS termination)
        │
        ├── /ws/*   ──►  Daphne (ASGI)
        │                    │
        │                    ├── HTTP requests → Django views → PostgreSQL
        │                    └── WebSocket → Channels → Redis pub/sub
        │
        └── /api/*  ──►  Daphne (ASGI)
                             │
                             └── Django views
                                    │
                                    ├── PostgreSQL (primary store)
                                    ├── Redis (cache + sessions)
                                    └── S3 (media files)

Background Workers
    Celery Worker ◄── Redis Broker
        ├── generate_thumbnail    (image/video processing, S3 upload)
        ├── send_welcome_email    (SMTP)
        └── send_notification_*  (SMTP)

    Celery Beat ──► expire_stories (runs every 15 min)
```
