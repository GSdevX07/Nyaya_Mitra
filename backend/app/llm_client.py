"""The single, configuration-driven gateway for Nyaya Mitra model calls.

Every response reports the provider that actually generated it.  If no model is
available, the gateway returns only a review-required operational notice; it
never substitutes pre-written legal advice or translations for an AI response.
"""

from __future__ import annotations

import os
import warnings

# Suppress verbose oneDNN and TensorFlow informational messages
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore")

from pathlib import Path
from typing import Callable

import requests
from dotenv import load_dotenv
from groq import Groq

# Load backend/.env or cwd .env
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
load_dotenv()

_last_provider = "not-called"


def get_last_provider() -> str:
    return _last_provider


def _call_watsonx(prompt: str, system: str) -> str:
    api_key = os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    model_id = os.getenv("WATSONX_MODEL_ID")
    endpoint = os.getenv("WATSONX_URL")
    if not all((api_key, project_id, model_id, endpoint)):
        raise RuntimeError("watsonx requires WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_MODEL_ID, and WATSONX_URL")

    token_response = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": api_key},
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        timeout=float(os.getenv("WATSONX_TIMEOUT_SECONDS", "30")),
    )
    token_response.raise_for_status()
    access_token = token_response.json()["access_token"]
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    response = requests.post(
        f"{endpoint.rstrip('/')}/ml/v1/text/chat",
        params={"version": os.getenv("WATSONX_API_VERSION", "2024-05-31")},
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json", "Accept": "application/json"},
        json={
            "model_id": model_id,
            "project_id": project_id,
            "messages": messages,
            "parameters": {"temperature": float(os.getenv("LLM_TEMPERATURE", "0.1"))},
        },
        timeout=float(os.getenv("WATSONX_TIMEOUT_SECONDS", "30")),
    )
    response.raise_for_status()
    payload = response.json()
    content = payload.get("choices", [{}])[0].get("message", {}).get("content")
    if isinstance(content, list):
        content = "".join(item.get("text", "") for item in content if isinstance(item, dict))
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("watsonx response did not contain generated text")
    return content.strip()


def _call_groq(prompt: str, system: str) -> str:
    import re

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Groq requires GROQ_API_KEY")

    configured_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    candidate_models = [configured_model]
    for fallback in ["openai/gpt-oss-120b", "groq/compound-mini", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    client = Groq(api_key=api_key)
    last_err: Exception | None = None
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]

    for model in candidate_models:
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
                timeout=float(os.getenv("GROQ_TIMEOUT_SECONDS", "15")),
            )
            content = completion.choices[0].message.content
            if content and content.strip():
                cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                return cleaned if cleaned else content.strip()
        except Exception as exc:
            last_err = exc
            continue

    raise RuntimeError(f"Groq generation failed across models {candidate_models}: {last_err}")


def _segment_text_lines(image: "Image.Image") -> "list[Image.Image]":  # type: ignore[name-defined]
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
    lines: list[Image.Image] = []
    
    for (x, y, w, h) in boxes:
        # Add padding around the text for better TrOCR recognition context
        x1 = max(0, x - PAD)
        y1 = max(0, y - PAD)
        x2 = min(image.width, x + w + PAD)
        y2 = min(image.height, y + h + PAD)
        
        # Crop directly from the original PIL image to preserve RGB quality
        lines.append(image.crop((x1, y1, x2, y2)))

    return lines if len(lines) >= 1 else [image]


def ocr_image_via_easyocr(image_bytes: bytes) -> str:
    """Extract text from an image using EasyOCR.
    
    EasyOCR is a robust PyTorch-based OCR engine that handles both printed 
    text and block-letter handwriting gracefully without the severe hallucination
    biases (like generating receipts or cursive) seen in TrOCR models.
    """
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    import easyocr
    import numpy as np
    import cv2
    import warnings
    warnings.filterwarnings("ignore")
    
    # Cache the reader in memory to avoid reloading it on every request
    if not hasattr(ocr_image_via_easyocr, "_reader"):
        ocr_image_via_easyocr._reader = easyocr.Reader(['en'], gpu=False, verbose=False)  # type: ignore[attr-defined]

    reader = ocr_image_via_easyocr._reader  # type: ignore[attr-defined]
    
    # Read bytes into an OpenCV matrix
    nparr = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_cv is None:
        raise ValueError("Could not decode image file")
    
    # Run text extraction with paragraph grouping for cleaner output
    results = reader.readtext(img_cv, detail=0, paragraph=True)
    return "\n\n".join(str(r) for r in results)


def _call_ollama(prompt: str, system: str) -> str:
    model = os.getenv("OLLAMA_MODEL")
    if not model:
        raise RuntimeError("Ollama requires OLLAMA_MODEL")
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    response = requests.post(
        os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat"),
        json={"model": model, "messages": messages, "stream": False, "options": {"temperature": float(os.getenv("LLM_TEMPERATURE", "0.1"))}},
        timeout=float(os.getenv("OLLAMA_TIMEOUT", "60")),
    )
    response.raise_for_status()
    payload = response.json()
    content = payload.get("message", {}).get("content") or payload.get("response")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Ollama response did not contain generated text")
    return content.strip()


def generate(prompt: str, system: str = "", _override: str | None = None) -> str:
    """Generate through the configured provider order: watsonx, Groq, then Ollama."""
    global _last_provider
    if _override is not None:
        _last_provider = "test override"
        return _override

    providers: dict[str, Callable[[str, str], str]] = {
        "watsonx": _call_watsonx,
        "groq": _call_groq,
        "ollama": _call_ollama,
    }
    errors: list[str] = []
    for name in (item.strip().lower() for item in os.getenv("LLM_PROVIDER_ORDER", "watsonx,groq,ollama").split(",")):
        call = providers.get(name)
        if call is None:
            errors.append(f"unknown provider '{name}'")
            continue
        try:
            content = call(prompt, system)
            _last_provider = name if name != "ollama" else f"ollama:{os.getenv('OLLAMA_MODEL')}"
            return content
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    _last_provider = "unavailable"
    return os.getenv("LLM_UNAVAILABLE_MESSAGE", "AI generation is unavailable. A qualified human reviewer must complete this step.")
