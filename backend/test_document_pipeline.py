"""
test_document_pipeline.py Verification script for document processing pipeline.
"""

from app.document_pipeline import execute_full_document_pipeline

def test_pipeline():
    print("Testing 7-Stage Legal Document Assessment Pipeline...")
    res = execute_full_document_pipeline(
        file_bytes=b"%PDF-1.4 sample content",
        document_name="UTP-0007_Handwritten_Remand.pdf",
        provided_text="Remand application and custody record for accused under Section 479 BNSS 2023 for bail eligibility review.",
    )


    print(f"[OK] Document Name: {res.document_name}")
    print(f"[OK] Is Scanned/Handwritten: {res.is_scanned_handwritten} (Confidence: {res.detection_confidence})")
    print(f"[OK] OCR Engine: {res.ocr_engine_used}")
    print(f"[OK] Data Prep Kit Status: {res.structured_metadata.get('data_prep_kit_status')}")
    print(f"[OK] RAG Citations Found: {len(res.rag_statute_citations)}")
    print(f"[OK] IBM Granite Model: {res.granite_assessment['model_name']}")
    print(f"[OK] Eligibility Status: {res.granite_assessment['eligibility_status']}")
    print(f"[OK] Urgency Rating: {res.granite_assessment['urgency_rating']}")
    print(f"[OK] Total Processing Time: {res.processing_time_ms} ms")

if __name__ == "__main__":
    test_pipeline()
