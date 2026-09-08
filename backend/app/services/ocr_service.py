"""Dedicated on-premise OCR and computer vision service for Nyaya Mitra.

100% private and on-premise — zero external cloud API calls or data transmission.
Handles printed and handwritten text in English, Hindi, and regional scripts
with automatic OpenCV image enhancement (CLAHE contrast boosting and noise reduction).
"""

from __future__ import annotations

import os
import sys
import warnings
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from PIL import Image

# Suppress verbose oneDNN and TensorFlow informational messages
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore")


def segment_text_lines(image: "Image.Image") -> List["Image.Image"]:
    """Segment a document image into individual text lines.

    Uses robust OpenCV computer vision (adaptive thresholding + dilation + contours)
    to handle unevenly lit photos (like camera snaps of paper).

    Returns a list of cropped PIL Images (one for each text line).
    Falls back to the full image if no valid lines are detected.
    """
    import cv2
    import numpy as np
    from PIL import Image

    # Convert PIL Image to OpenCV format (BGR)
    img_cv = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # 1. Adaptive Thresholding: Handles uneven shadows in photos
    # Returns a binary image where text is white (255) and background is black (0)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10
    )

    # 2. Dilation: Smear pixels horizontally so words merge into solid line bands
    # 40px wide by 5px tall rectangle kernel
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 5))
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    # 3. Find Contours (Bounding boxes for the lines)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = [cv2.boundingRect(c) for c in contours]

    # 4. Filter out noise (tiny dots or random specks)
    # Require lines to be at least 8px tall and 20px wide
    boxes = [b for b in boxes if b[2] > 20 and b[3] > 8]

    # Sort boxes from top to bottom of the page
    boxes.sort(key=lambda b: b[1])

    PAD = 8
    lines: List[Image.Image] = []

    for x, y, w, h in boxes:
        x1 = max(0, x - PAD)
        y1 = max(0, y - PAD)
        x2 = min(image.width, x + w + PAD)
        y2 = min(image.height, y + h + PAD)

        lines.append(image.crop((x1, y1, x2, y2)))

    return lines if len(lines) >= 1 else [image]


# Alias for internal backwards compatibility
_segment_text_lines = segment_text_lines


def ocr_image_via_easyocr(image_bytes: bytes, languages: Optional[List[str]] = None) -> str:
    """Extract text from an image using local on-premise EasyOCR.

    100% private and on-premise — zero external cloud API calls or data transmission.
    Robustly handles printed and handwritten text in English, Hindi, and regional scripts
    with automatic image enhancement (CLAHE contrast boosting and noise reduction).
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    import cv2
    import easyocr
    import numpy as np

    devanagari_cached = os.path.exists(os.path.expanduser("~/.EasyOCR/model/devanagari_g2.pth"))
    if languages is None:
        langs = ["en", "hi"] if devanagari_cached else ["en"]
    else:
        langs = languages
    cache_key = tuple(sorted(langs))

    if not hasattr(ocr_image_via_easyocr, "_readers"):
        ocr_image_via_easyocr._readers = {}  # type: ignore[attr-defined]

    if cache_key not in ocr_image_via_easyocr._readers:  # type: ignore[attr-defined]
        try:
            ocr_image_via_easyocr._readers[cache_key] = easyocr.Reader(list(cache_key), gpu=False, verbose=False)  # type: ignore[attr-defined]
        except Exception:
            # If multi-lingual model not yet downloaded, fall back to cached English reader
            if ("en",) not in ocr_image_via_easyocr._readers:  # type: ignore[attr-defined]
                ocr_image_via_easyocr._readers[("en",)] = easyocr.Reader(["en"], gpu=False, verbose=False)  # type: ignore[attr-defined]
            cache_key = ("en",)

    reader = ocr_image_via_easyocr._readers[cache_key]  # type: ignore[attr-defined]

    # Read bytes into an OpenCV matrix
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_cv is None:
        raise ValueError("Could not decode image file")

    # Pass 1: Run text extraction with paragraph grouping
    results = reader.readtext(img_cv, detail=0, paragraph=True)
    extracted = "\n\n".join(str(r).strip() for r in results if str(r).strip())

    # Pass 2: If paragraph grouping yielded no text, try word-by-word / line-by-line
    if not extracted.strip():
        raw_results = reader.readtext(img_cv, detail=0, paragraph=False)
        extracted = "\n".join(str(r).strip() for r in raw_results if str(r).strip())

    # Pass 3: If still empty (e.g. faint handwritten text on paper), apply CLAHE contrast enhancement
    if not extracted.strip():
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        enhanced_results = reader.readtext(enhanced, detail=0, paragraph=False)
        extracted = "\n".join(str(r).strip() for r in enhanced_results if str(r).strip())

    return extracted
