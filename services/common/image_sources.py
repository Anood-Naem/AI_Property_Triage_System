"""Image input parsing: HTTP(S) URLs and base64 uploads (shared across services)."""

from __future__ import annotations

import base64
import binascii
import re
from typing import Any

from pydantic import BaseModel, Field, model_validator

DATA_URI_RE = re.compile(r"^data:([^;]+);base64,(.+)$", re.DOTALL | re.IGNORECASE)
ALLOWED_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/bmp",
        "image/tiff",
    }
)
MAX_IMAGE_BYTES = 10 * 1024 * 1024


class ImageSource(BaseModel):
    """Exactly one of image_url or image_base64 must be set."""

    image_url: str | None = Field(default=None, max_length=2048)
    image_base64: str | None = Field(default=None, max_length=20_000_000)
    mime_type: str | None = Field(default=None, max_length=128)
    filename: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_source(self) -> ImageSource:
        url = (self.image_url or "").strip()
        b64 = (self.image_base64 or "").strip()
        has_url = bool(url)
        has_b64 = bool(b64)

        if has_url and has_b64:
            raise ValueError("Provide either image_url or image_base64, not both")
        if not has_url and not has_b64:
            raise ValueError("Provide image_url or image_base64")

        if has_url and not url.startswith(("http://", "https://")):
            raise ValueError("image_url must be http or https")
        self.image_url = url or None

        if has_b64:
            mime = (self.mime_type or "").strip().lower()
            data_uri_match = DATA_URI_RE.match(b64)
            if data_uri_match and not mime:
                mime = data_uri_match.group(1).strip().lower()
            if not mime:
                raise ValueError(
                    "mime_type is required when image_base64 is provided "
                    "(unless using a data:...;base64,... URI)"
                )
            if mime not in ALLOWED_MIME_TYPES:
                allowed = ", ".join(sorted(ALLOWED_MIME_TYPES))
                raise ValueError(f"mime_type must be one of: {allowed}")
            self.mime_type = mime
            self.image_base64 = b64

        if self.filename:
            safe = self.filename.replace("\\", "/").split("/")[-1].strip()
            if not safe or safe in (".", ".."):
                raise ValueError("filename must be a valid file name")
            self.filename = safe[:255]

        return self

    @property
    def source_kind(self) -> str:
        return "url" if self.image_url else "base64"

    def display_label(self) -> str:
        if self.image_url:
            return self.image_url
        return self.filename or "upload"

    def decode_bytes(self) -> tuple[bytes, str]:
        if self.image_url:
            raise ValueError("decode_bytes() is only for image_base64 sources")

        payload = (self.image_base64 or "").strip()
        mime = (self.mime_type or "").lower()

        match = DATA_URI_RE.match(payload)
        if match:
            mime = match.group(1).strip().lower()
            payload = match.group(2).strip()
            if mime not in ALLOWED_MIME_TYPES:
                allowed = ", ".join(sorted(ALLOWED_MIME_TYPES))
                raise ValueError(f"data URI mime type must be one of: {allowed}")

        try:
            raw = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("image_base64 is not valid base64") from exc

        if len(raw) > MAX_IMAGE_BYTES:
            raise ValueError(f"Image exceeds {MAX_IMAGE_BYTES // (1024 * 1024)}MB limit")
        if len(raw) == 0:
            raise ValueError("image_base64 decoded to empty content")

        return raw, mime

    def to_result_meta(self) -> dict[str, Any]:
        return {
            "image_url": self.image_url,
            "filename": self.filename,
            "source": self.source_kind,
        }

    def to_analyse_payload(self) -> dict[str, Any]:
        """JSON body for image service POST /analyse."""
        if self.image_url:
            return {"image_url": self.image_url}
        return {
            "image_base64": self.image_base64,
            "mime_type": self.mime_type,
            "filename": self.filename,
        }
