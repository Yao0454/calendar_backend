import base64
import io
import logging

from PIL import Image

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 1 * 1024 * 1024  # 1 MB


def compress_image_base64(image_b64: str, mime: str) -> tuple[str, str]:
    raw = base64.b64decode(image_b64)
    if len(raw) <= MAX_IMAGE_BYTES:
        return image_b64, mime

    img = Image.open(io.BytesIO(raw))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    quality = 85
    while quality >= 20:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        if buf.tell() <= MAX_IMAGE_BYTES:
            break
        quality -= 10
    else:
        # Scale down if quality reduction wasn't enough
        scale = (MAX_IMAGE_BYTES / buf.tell()) ** 0.5  # type: ignore
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)  # type: ignore
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)

    compressed = base64.b64encode(buf.getvalue()).decode()
    logger.info("Image compressed: %d -> %d bytes", len(raw), buf.tell())
    return compressed, "image/jpeg"


def extract_pdf_text(file_b64: str) -> str:
    import fitz  # pymupdf

    raw = base64.b64decode(file_b64)
    doc = fitz.open(stream=raw, filetype="pdf")
    pages_text = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages_text)  # type: ignore
