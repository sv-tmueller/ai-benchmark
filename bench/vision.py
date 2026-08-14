"""Multi-modal image support for vision-capable LLM benchmarks.

Provides utilities to encode local image files or remote URLs into the
data-URI / URL formats expected by the OpenAI vision API, and to assemble
the ``messages`` array consumed by chat-completions endpoints.

Stdlib-only: :mod:`base64`, :mod:`mimetypes`, :mod:`pathlib`, :mod:`warnings`.
"""

from __future__ import annotations

import base64
import mimetypes
import warnings
from pathlib import Path
from typing import List, Optional, Sequence, Union

__all__ = [
    "MAX_IMAGE_SIZE_BYTES",
    "encode_image_file",
    "encode_image_url",
    "build_vision_messages",
    "load_images_from_prompt",
]

#: Hard ceiling (4 MB) beyond which a :class:`UserWarning` is emitted.
MAX_IMAGE_SIZE_BYTES: int = 4_000_000


# ---------------------------------------------------------------------------
# Extension → MIME-type mapping.
#
# ``mimetypes`` covers the common cases on most platforms, but we maintain an
# explicit fallback table so behaviour is deterministic regardless of the host
# OS or whether the optional ``/etc/mime.types`` file is present.
# ---------------------------------------------------------------------------
_EXT_MIME: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".jfif": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _guess_mime(path: Union[str, Path]) -> str:
    """Return the MIME type for *path*, preferring the extension table."""
    ext = Path(str(path)).suffix.lower()
    if ext in _EXT_MIME:
        return _EXT_MIME[ext]
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def encode_image_file(path: Union[str, Path]) -> str:
    """Read *path* from disk and return a base64 ``data:`` URI.

    Parameters
    ----------
    path:
        Filesystem location of the image.

    Returns
    -------
    str
        ``data:<mime>;base64,<payload>`` suitable for inclusion in an
        ``image_url`` content entry.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image file not found: {p}")

    size = p.stat().st_size
    if size > MAX_IMAGE_SIZE_BYTES:
        warnings.warn(
            f"Image '{p.name}' is {size:,} bytes which exceeds "
            f"MAX_IMAGE_SIZE_BYTES ({MAX_IMAGE_SIZE_BYTES:,}). "
            "Some APIs may reject or truncate the payload.",
            UserWarning,
            stacklevel=2,
        )

    mime = _guess_mime(p)
    encoded = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def encode_image_url(url: str) -> str:
    """Pass *url* through unchanged.

    Remote URLs are referenced directly by the vision API—no local download
    or re-encoding is required.
    """
    return url


def build_vision_messages(
    system_text: Optional[str],
    user_text: str,
    image_data_uris: Sequence[str],
) -> list:
    """Build an OpenAI-format ``messages`` list with mixed content.

    Layout::

        [{"role": "system", "content": "..."}]   # only if system_text
        [{"role": "user", "content": [
            {"type": "text", "text": "..."},
            {"type": "image_url", "image_url": {"url": "<uri>"}},
            ...
        ]}]

    Parameters
    ----------
    system_text:
        Optional system-prompt string.  When falsy (``None``/``""``) the
        system message is omitted entirely.
    user_text:
        Text portion of the user message.
    image_data_uris:
        Iterable of data URIs or remote URLs produced by
        :func:`encode_image_file` / :func:`encode_image_url`.

    Returns
    -------
    list
        Ready-to-send ``messages`` array.
    """
    messages: list = []

    if system_text:
        messages.append({"role": "system", "content": system_text})

    content: list = [{"type": "text", "text": user_text}]
    for uri in image_data_uris:
        content.append({
            "type": "image_url",
            "image_url": {"url": uri},
        })

    messages.append({"role": "user", "content": content})
    return messages


def load_images_from_prompt(
    prompt_data: dict,
    prompts_dir: Union[str, Path],
) -> List[str]:
    """Extract image data URIs declared in a prompt TOML ``[images]`` block.

    Expected schema::

        [images]
        files = ["cat.png", "diagram.jpg"]
        urls  = ["https://example.com/photo.webp"]

    Local file names are resolved relative to ``prompts_dir/assets/``.

    Parameters
    ----------
    prompt_data:
        Parsed TOML dictionary representing a single prompt definition.
    prompts_dir:
        Directory whose ``assets/`` sub-folder holds the referenced files.

    Returns
    -------
    list[str]
        Ordered concatenation of encoded local files followed by remote URLs.
        Empty list when no ``[images]`` block is present.
    """
    uris: List[str] = []
    images_cfg = prompt_data.get("images") or {}

    assets_dir = Path(prompts_dir) / "assets"

    # ----- local files -------------------------------------------------
    for fname in images_cfg.get("files", []) or []:
        uris.append(encode_image_file(assets_dir / fname))

    # ----- remote URLs --------------------------------------------------
    for url in images_cfg.get("urls", []) or []:
        uris.append(encode_image_url(url))

    return uris
