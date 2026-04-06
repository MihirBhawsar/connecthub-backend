"""
Shared utility functions for ConnectHub.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Allowed MIME types for media uploads
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/aac"}
ALLOWED_MEDIA_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES | ALLOWED_AUDIO_TYPES

# Maximum file sizes in bytes
MAX_IMAGE_SIZE = 10_000_000   # 10 MB
MAX_VIDEO_SIZE = 500_000_000  # 500 MB
MAX_AUDIO_SIZE = 50_000_000   # 50 MB

# Hashtag regex
HASHTAG_PATTERN = re.compile(r"#(\w+)")


def extract_hashtags(text: str) -> list[str]:
    """
    Extract all hashtag names from a piece of text.

    Args:
        text: The text to search for hashtags.

    Returns:
        A list of lowercase hashtag names (without the # symbol).
    """
    return [tag.lower() for tag in HASHTAG_PATTERN.findall(text)]


def validate_file_type(file_obj, allowed_types: set[str]) -> Optional[str]:
    """
    Validate the MIME type of an uploaded file by reading magic bytes.

    Args:
        file_obj: Django InMemoryUploadedFile or similar.
        allowed_types: Set of allowed MIME type strings.

    Returns:
        The detected MIME type string if valid, raises ValueError otherwise.
    """
    try:
        import magic
        header = file_obj.read(1024)
        file_obj.seek(0)
        mime_type = magic.from_buffer(header, mime=True)
    except ImportError:
        # python-magic not installed — fall back to content_type header (less secure)
        logger.warning("python-magic not installed; falling back to content_type for file validation.")
        mime_type = getattr(file_obj, "content_type", "application/octet-stream")

    if mime_type not in allowed_types:
        raise ValueError(f"Unsupported file type: {mime_type}. Allowed: {sorted(allowed_types)}")

    return mime_type


def get_max_file_size(mime_type: str) -> int:
    """
    Return the maximum allowed file size for a given MIME type.

    Args:
        mime_type: The MIME type string.

    Returns:
        Maximum allowed size in bytes.
    """
    if mime_type in ALLOWED_IMAGE_TYPES:
        return MAX_IMAGE_SIZE
    if mime_type in ALLOWED_VIDEO_TYPES:
        return MAX_VIDEO_SIZE
    if mime_type in ALLOWED_AUDIO_TYPES:
        return MAX_AUDIO_SIZE
    return MAX_IMAGE_SIZE
