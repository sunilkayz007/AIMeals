"""
=========================================================
AIMeals Backend
Image Format Conversion Utility

Converts an uploaded image to a format Claude's vision API
accepts (image/jpeg, image/png, image/gif, image/webp) when
it arrives as something else -- in practice this exists
almost entirely for HEIC/HEIF photos straight off an iPhone
(Camera format set to "High Efficiency", the default since
iOS 11 -- Claude's API rejects that media_type outright with
a 400, which is what analyze_food_image() and
identify_ingredients_from_image() were hitting before this
existed).

pillow-heif registers a HEIF/HEIC opener with Pillow so
Image.open() can decode it exactly like a JPEG or PNG; the
decoded image is then re-encoded as a plain JPEG. Both
libraries ship pre-built wheels for Windows/macOS/Linux --
no system libheif install required.

This is deliberately generic (Image.open() + convert, not a
HEIC-specific code path) so it also covers any other odd
format a phone's camera app might produce (e.g. BMP/TIFF) --
if Pillow can decode it, this can normalize it for Claude.

Dependencies:
    - Pillow
    - pillow-heif
=========================================================
"""

import io
from typing import Tuple

from PIL import Image
import pillow_heif

from app.core.exceptions import UnsupportedImageFormatError

pillow_heif.register_heif_opener()

# Media types Claude's vision API accepts directly.
CLAUDE_SUPPORTED_IMAGE_MEDIA_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}


def ensure_claude_supported_image(image_bytes: bytes, media_type: str) -> Tuple[bytes, str]:
    """
    Returns (image_bytes, media_type) guaranteed to be one Claude's
    vision API accepts.

    If media_type is already supported, returns the input completely
    unchanged (no re-encoding, no quality loss) -- the common case
    for the vast majority of Android/web uploads.

    Otherwise attempts to decode the bytes with Pillow (HEIC/HEIF
    via pillow_heif's registered opener, or whatever else Pillow
    recognizes) and re-encode as JPEG.

    Raises:
        UnsupportedImageFormatError: if the bytes can't be decoded
            at all -- a genuinely corrupt or non-image upload.
            Checked BEFORE any credit is spent by every caller.
    """
    if media_type in CLAUDE_SUPPORTED_IMAGE_MEDIA_TYPES:
        return image_bytes, media_type

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.load()
            rgb = img.convert("RGB")
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=90)
            return buffer.getvalue(), "image/jpeg"
    except Exception as e:
        raise UnsupportedImageFormatError(
            f"'{media_type}' photos aren't supported and this one "
            f"couldn't be converted automatically ({e}). Please "
            f"retake the photo or choose a different one."
        ) from e
