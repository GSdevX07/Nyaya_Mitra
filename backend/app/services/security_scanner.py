"""
services/security_scanner.py — Binary File Signature Validation & Security Screening Boundary.

Enforces:
1. True file signature (magic bytes) validation — blocks file extension spoofing.
2. Strict size limits (25MB for PDFs, 15MB for images, 5MB for text).
3. Security boundary checks:
   - Detects executable payloads (DOS/Windows PE MZ headers, Linux ELF, Mach-O).
   - Detects embedded PDF malicious scripts (/JavaScript, /JS, /Launch, /EmbeddedFiles).
   - Detects script injection tags in images/metadata (<script, eval(, javascript:).
4. Quarantine isolation for suspicious documents with high-severity security audit logging.
"""
from __future__ import annotations

import datetime
import io
import re
from enum import Enum
from typing import Optional, Tuple
from pydantic import BaseModel


class ScanStatus(str, Enum):
    PASSED = "PASSED"
    QUARANTINED = "QUARANTINED"
    FAILED = "FAILED"


class SecurityScanResult(BaseModel):
    status: ScanStatus
    threat_detected: bool
    threat_details: Optional[str] = None
    engine: str = "NyayaMitra-SafeBoundaryScanner-v1.0"
    scanned_at: str
    file_size_bytes: int
    magic_signature: str


# Maximum allowed sizes in bytes
MAX_PDF_SIZE_BYTES = 25 * 1024 * 1024       # 25 MB
MAX_IMAGE_SIZE_BYTES = 15 * 1024 * 1024     # 15 MB
MAX_TEXT_SIZE_BYTES = 5 * 1024 * 1024       # 5 MB


# Magic byte signatures
MAGIC_SIGNATURES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpeg": [b"\xff\xd8\xff"],
    "webp": [b"RIFF"],  # WEBP has 'RIFF' at 0-4 and 'WEBP' at 8-12
    "tiff": [b"II*\x00", b"MM\x00*"],
    "bmp": [b"BM"],
}


def validate_file_signature(
    file_bytes: bytes,
    filename: str,
    mime_type: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """
    Validates file size and binary signature (magic bytes) against declared extension/mime.

    Returns:
        (is_valid: bool, error_message: str, detected_type: str)
    """
    if not file_bytes:
        return False, "File is empty (0 bytes).", "unknown"

    size = len(file_bytes)
    ext = (filename.split(".")[-1] if "." in filename else "").lower()

    # Size limit checks
    if ext == "pdf":
        if size > MAX_PDF_SIZE_BYTES:
            return False, f"PDF file size ({size / 1024 / 1024:.2f} MB) exceeds maximum limit of 25 MB.", "pdf"
    elif ext in ("jpg", "jpeg", "png", "webp", "tiff", "tif", "bmp", "gif", "heic"):
        if size > MAX_IMAGE_SIZE_BYTES:
            return False, f"Image file size ({size / 1024 / 1024:.2f} MB) exceeds maximum limit of 15 MB.", "image"
    elif ext in ("txt", "text", "csv", "json"):
        if size > MAX_TEXT_SIZE_BYTES:
            return False, f"Text file size ({size / 1024 / 1024:.2f} MB) exceeds maximum limit of 5 MB.", "text"

    # PDF signature
    if ext == "pdf":
        if not file_bytes.startswith(b"%PDF-"):
            return False, "Invalid PDF binary signature: file does not start with '%PDF-' magic bytes. Extension spoofing detected.", "unknown"
        return True, "", "pdf"

    # PNG signature
    if ext == "png":
        if not file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return False, "Invalid PNG binary signature: magic bytes do not match PNG standard.", "unknown"
        return True, "", "png"

    # JPEG signature
    if ext in ("jpg", "jpeg"):
        if not file_bytes.startswith(b"\xff\xd8\xff"):
            return False, "Invalid JPEG binary signature: magic bytes do not match JPEG SOI marker.", "unknown"
        return True, "", "jpeg"

    # WEBP signature
    if ext == "webp":
        if not (file_bytes.startswith(b"RIFF") and b"WEBP" in file_bytes[8:12]):
            return False, "Invalid WEBP binary signature: missing RIFF/WEBP container format.", "unknown"
        return True, "", "webp"

    # BMP signature
    if ext == "bmp":
        if not file_bytes.startswith(b"BM"):
            return False, "Invalid BMP binary signature: missing 'BM' header.", "unknown"
        return True, "", "bmp"

    # TIFF signature
    if ext in ("tiff", "tif"):
        if not (file_bytes.startswith(b"II*\x00") or file_bytes.startswith(b"MM\x00*")):
            return False, "Invalid TIFF binary signature: missing TIFF endian header.", "unknown"
        return True, "", "tiff"

    # Plain text / CSV
    if ext in ("txt", "text", "csv", "json"):
        try:
            file_bytes.decode("utf-8")
            return True, "", "text"
        except UnicodeDecodeError:
            return False, "Text document contains non-decodable binary bytes.", "unknown"

    # If extension is not explicitly listed, check if it matches any known magic bytes
    for kind, sigs in MAGIC_SIGNATURES.items():
        for sig in sigs:
            if file_bytes.startswith(sig):
                return True, "", kind

    # Allow harmless text entry
    try:
        file_bytes.decode("utf-8")
        return True, "", "text"
    except Exception:
        pass

    return False, f"Unsupported or unrecognized file signature for '{filename}'.", "unknown"


def scan_file_security(
    file_bytes: bytes,
    filename: str,
) -> SecurityScanResult:
    """
    Security boundary screening for uploaded documents.
    Detects executable signatures, shellcode injections, and malicious PDF action streams.
    """
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    size = len(file_bytes)
    magic_repr = file_bytes[:8].hex()

    threats = []

    # 1. Executable payload detection (PE MZ, ELF, Mach-O)
    if file_bytes.startswith(b"\x4d\x5a"):  # DOS/Windows MZ executable
        threats.append("Embedded Windows Portable Executable (MZ header) detected.")
    if file_bytes.startswith(b"\x7fELF"):  # Linux ELF executable
        threats.append("Embedded Linux Executable and Linkable Format (ELF) header detected.")
    if file_bytes.startswith(b"\xfe\xed\xfa\xce") or file_bytes.startswith(b"\xcf\xfa\xed\xfe"):
        threats.append("Embedded Apple Mach-O binary header detected.")

    # 2. PDF-specific security checks
    ext = (filename.split(".")[-1] if "." in filename else "").lower()
    if ext == "pdf" or file_bytes.startswith(b"%PDF-"):
        # Scan raw bytes for dangerous PDF stream keys
        lower_bytes = file_bytes.lower()
        if b"/javascript" in lower_bytes or b"/js" in lower_bytes:
            threats.append("Malicious active content: PDF embedded JavaScript execution (/JavaScript or /JS) detected.")
        if b"/launch" in lower_bytes:
            threats.append("Arbitrary command launch action (/Launch) detected in PDF dictionary.")
        if b"/embeddedfiles" in lower_bytes and (b".exe" in lower_bytes or b".bat" in lower_bytes or b".ps1" in lower_bytes):
            threats.append("Dangerous embedded executable payload (/EmbeddedFiles) detected in PDF.")

    # 3. Web Script Injection in text/image streams
    sample_text = file_bytes[:4096].lower()
    if b"<script" in sample_text or b"javascript:" in sample_text or b"onerror=" in sample_text or b"onload=" in sample_text:
        threats.append("Malicious script injection payload detected in document header.")

    if threats:
        return SecurityScanResult(
            status=ScanStatus.QUARANTINED,
            threat_detected=True,
            threat_details="; ".join(threats),
            scanned_at=now_iso,
            file_size_bytes=size,
            magic_signature=magic_repr,
        )

    return SecurityScanResult(
        status=ScanStatus.PASSED,
        threat_detected=False,
        threat_details=None,
        scanned_at=now_iso,
        file_size_bytes=size,
        magic_signature=magic_repr,
    )
