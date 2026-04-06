"""
Celery tasks for the posts app.

Tasks:
    generate_thumbnail — create a thumbnail for image/video posts
    expire_stories     — delete expired stories (Celery Beat, every 15 min)
"""
import io
import logging

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

logger = logging.getLogger(__name__)

THUMBNAIL_SIZE = (400, 400)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_thumbnail(self, post_id: int) -> None:
    """
    Generate a thumbnail for image or video posts after upload.

    For images: resize to 400x400 using Pillow, preserving aspect ratio.
    For videos: this placeholder logs a warning (full ffmpeg implementation
                requires ffmpeg binary available in the container).

    Saves the thumbnail back to S3 and updates post.thumbnail.

    Args:
        post_id: Primary key of the Post to generate a thumbnail for.
    """
    from apps.posts.models import Post

    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        # Post deleted before the task ran — nothing to do
        return

    if not post.media_file:
        return

    try:
        if post.media_type == "image":
            _generate_image_thumbnail(post)
        elif post.media_type == "video":
            _generate_video_thumbnail(post)
    except Exception as exc:
        logger.warning("Thumbnail generation failed for Post(%s): %s", post_id, exc)
        raise self.retry(exc=exc)


def _generate_image_thumbnail(post) -> None:
    """Resize post image to THUMBNAIL_SIZE using Pillow and save to storage."""
    from PIL import Image

    with default_storage.open(post.media_file.name) as media_file:
        with Image.open(media_file) as img:
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Convert to RGB to support JPEG output for all image types
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            buffer.seek(0)

    thumbnail_name = f"thumbnails/{post.id}_thumb.jpg"
    saved_name = default_storage.save(thumbnail_name, ContentFile(buffer.read()))

    from apps.posts.models import Post
    Post.objects.filter(pk=post.pk).update(thumbnail=saved_name)
    logger.info("Thumbnail generated for Post(%s): %s", post.pk, saved_name)


def _generate_video_thumbnail(post) -> None:
    """
    Extract the first frame of a video as a thumbnail using ffmpeg subprocess.

    Requires ffmpeg to be installed in the container (included in Dockerfile).
    """
    import os
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input_video")
        output_path = os.path.join(tmpdir, "thumb.jpg")

        # Download the video file from storage to temp dir
        with default_storage.open(post.media_file.name) as src:
            with open(input_path, "wb") as dst:
                dst.write(src.read())

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-ss", "00:00:01",
                "-vframes", "1",
                "-vf", f"scale={THUMBNAIL_SIZE[0]}:{THUMBNAIL_SIZE[1]}:force_original_aspect_ratio=decrease",
                output_path,
            ],
            capture_output=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()}")

        with open(output_path, "rb") as thumb_file:
            thumbnail_name = f"thumbnails/{post.id}_thumb.jpg"
            saved_name = default_storage.save(thumbnail_name, ContentFile(thumb_file.read()))

    from apps.posts.models import Post
    Post.objects.filter(pk=post.pk).update(thumbnail=saved_name)
    logger.info("Video thumbnail generated for Post(%s): %s", post.pk, saved_name)


@shared_task
def expire_stories() -> None:
    """
    Delete stories that have passed their expiry time.

    This task is scheduled to run every 15 minutes via Celery Beat.
    """
    from apps.posts.models import Story

    expired_count, _ = Story.objects.filter(expires_at__lte=timezone.now()).delete()
    if expired_count:
        logger.info("Deleted %d expired stories.", expired_count)
