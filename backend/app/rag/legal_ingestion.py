"""Legal-PDF ingestion: extraction -> configured IBM DPK -> Chroma indexing."""

from __future__ import annotations

import io
import os
import re
import subprocess
import tempfile
from pathlib import Path

from app.rag.vector_store import index_legal_text


class LegalIngestionError(ValueError):
    pass


def extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        raise LegalIngestionError("The uploaded PDF could not be read") from exc
    if not text:
        raise LegalIngestionError("No machine-readable text was found. OCR the scanned legal PDF before RAG ingestion.")
    return text


def run_data_prep_kit(text: str) -> tuple[str, str]:
    """Run the organisation's IBM DPK transform command, when configured.

    IBM DPK is a batch framework; the specific transform is deployment owned.
    `{input}` and `{output}` are injected as file paths, avoiding hard-coded
    transform parameters in the web service.
    """
    command_template = os.getenv("IBM_DPK_COMMAND")
    if not command_template:
        cleaned = re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()
        return cleaned, "NORMALISED_PENDING_IBM_DPK_CONFIGURATION"
    with tempfile.TemporaryDirectory(prefix="nyaya-dpk-") as temporary_directory:
        input_path = Path(temporary_directory) / "source.txt"
        output_path = Path(temporary_directory) / "prepared.txt"
        input_path.write_text(text, encoding="utf-8")
        command = command_template.format(input=input_path, output=output_path)
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=int(os.getenv("IBM_DPK_TIMEOUT_SECONDS", "300")))
        if result.returncode != 0:
            raise LegalIngestionError(f"IBM Data Prep Kit command failed: {result.stderr.strip()}")
        if not output_path.exists():
            raise LegalIngestionError("IBM Data Prep Kit did not write the configured output file")
        return output_path.read_text(encoding="utf-8").strip(), "IBM_DPK_COMPLETED"


def ingest_legal_pdf(document_id: str, source_name: str, content: bytes, source_url: str | None = None) -> dict:
    raw_text = extract_pdf_text(content)
    prepared_text, prep_status = run_data_prep_kit(raw_text)
    chunk_count = index_legal_text(document_id, source_name, prepared_text, source_url)
    return {"document_id": document_id, "source_name": source_name, "data_prep_status": prep_status, "chunks_indexed": chunk_count}
