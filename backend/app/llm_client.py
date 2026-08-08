"""
llm_client.py — Single choke-point for every LLM call in Nyaya Mitra.

Fault-tolerant 3-Tier Architecture:
  1. Primary Cloud Tier   : Groq API (llama-3.1-8b-instant) [8s timeout]
  2. Local Edge LLM Tier  : Ollama (granite4.1:8b) [15s timeout]
  3. Deterministic Safety : Pre-baked mock response (demo safety net)

No other file in the codebase should call an LLM API directly.
"""

from __future__ import annotations

import os
import requests
from dotenv import load_dotenv
from groq import Groq

# Load .env from backend/ directory
load_dotenv()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "granite4.1:8b")
OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "15.0"))


# ── Private provider implementations ─────────────────────────────────────────

def _call_primary(prompt: str, system: str) -> str:
    """
    Call the Groq API (Llama 3.1) for blazing fast inference.

    Timeout is set to 8s — fails fast if venue Wi-Fi dies so local fallbacks kick in.
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.1,   # Low temperature for legal exactness
        timeout=8.0,       # Fails fast if Wi-Fi dies
    )

    return completion.choices[0].message.content


def _call_ollama_fallback(prompt: str, system: str) -> str:
    """
    Call local Ollama server running granite4.1:8b model on host machine.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()

    if "message" in data and "content" in data["message"]:
        return data["message"]["content"]
    elif "response" in data:
        return data["response"]
    else:
        raise ValueError(f"Unexpected response payload from Ollama: {data}")


def _call_mock_fallback(prompt: str, system: str) -> str:
    """
    Mock fallback so the demo NEVER crashes even if cloud and local LLMs fail.
    """
    if "Draft a formal bail application" in prompt:
        return (
            "BAIL APPLICATION DRAFT\n"
            "IN THE COURT OF SESSIONS, SYNTHETIC JURISDICTION\n\n"
            "Subject: Application for Bail under Section 479 of the Bharatiya Nagarik Suraksha Sanhita (BNSS).\n\n"
            "May it please the Hon'ble Court,\n"
            "1. The applicant has been in custody as an undertrial prisoner.\n"
            "2. Under Section 479 BNSS, having served the requisite statutory threshold of the maximum sentence without conclusion of trial, the applicant is entitled to be released on bail.\n"
            "3. The applicant undertakes to comply with all conditions imposed by this Hon'ble Court.\n\n"
            "PRAYER:\n"
            "It is therefore most respectfully prayed that this Hon'ble Court may be pleased to grant bail to the applicant in the interest of justice."
        )
    elif "Target Language: hi" in prompt:
        return "आपके मामले की स्थिति: आप धारा 479 BNSS के तहत जमानत के पात्र हैं क्योंकि आपने अपनी अधिकतम सजा का आवश्यक हिस्सा पूरा कर लिया है। कानूनी सहायता वकील आपकी रिहाई के लिए जमानत अर्जी दायर करेंगे।"
    elif "Target Language: kn" in prompt:
        return "ನಿಮ್ಮ ಪ್ರಕರಣದ ಸ್ಥಿತಿ: ಸೆಕ್ಷನ್ 479 BNSS ಅಡಿಯಲ್ಲಿ ನೀವು ಜಾಮೀನಿಗೆ ಅರ್ಹರಾಗಿದ್ದೀರಿ, ಏಕೆಂದರೆ ನೀವು ನಿಮ್ಮ ಗರಿಷ್ಠ ಶಿಕ್ಷೆಯ ಅಗತ್ಯ ಭಾಗವನ್ನು ಪೂರೈಸಿದ್ದೀರಿ. ಕಾನೂನು ನೆರವು ವಕೀಲರು ನಿಮ್ಮ ಬಿಡುಗಡೆಗಾಗಿ ಜಾಮೀನು ಅರ್ಜಿಯನ್ನು ಸಲ್ಲಿಸುತ್ತಾರೆ."
    elif "Target Language: ta" in prompt:
        return "உங்கள் வழக்கின் நிலை: நீங்கள் அதிகபட்ச தண்டனையின் தேவையான பகுதியை நிறைவு செய்துள்ளதால், பிரிவு 479 BNSS-ன் கீழ் பிணை பெற தகுதியுடையவர். சட்ட உதவி வழக்கறிஞர் உங்கள் விடுதலைக்காக பிணை மனு தாக்கல் செய்வார்."
    elif "Target Language: te" in prompt:
        return "మీ కేసు స్థితి: మీరు గరిష్ట శిక్షలో అవసరమైన భాగాన్ని పూర్తి చేసినందున, సెక్షన్ 479 BNSS కింద బెయిల్‌కు అర్హులు. న్యాయ సహాయ న్యాయవాది మీ విడుదల కోసం బెయిల్ దరఖాస్తు దాఖలు చేస్తారు."
    else:
        # Default English fallback
        return "Case Status: You are eligible for bail under Section 479 BNSS, having served the required portion of your maximum sentence. A legal-aid lawyer will file a bail application on your behalf."


# ── Public interface — the ONLY function the rest of the codebase imports ─────

def generate(prompt: str, system: str = "", _override: str | None = None) -> str:
    """
    Universal LLM gateway with 3-tier transparent fallback:
      1. Primary Cloud Tier (Groq API — llama-3.1-8b-instant)
      2. Local Edge LLM Tier (Ollama — granite4.1:8b)
      3. Deterministic Pre-computed Safety Fallback
    """
    if _override is not None:
        return _override

    # Tier 1: Primary Cloud (Groq)
    try:
        return _call_primary(prompt, system)
    except Exception as e:
        print(f"\n[NETWORK WARNING] Primary Groq LLM failed: {e}")
        print("Attempting Tier 2 Local Edge Fallback (Ollama granite4.1:8b)...\n")

    # Tier 2: Local Edge LLM (Ollama granite4.1:8b)
    try:
        return _call_ollama_fallback(prompt, system)
    except Exception as e:
        print(f"\n[OLLAMA WARNING] Local Ollama fallback failed: {e}")
        print("Switching to Tier 3 Deterministic Safety Fallback...\n")

    # Tier 3: Deterministic Pre-computed Fallback
    return _call_mock_fallback(prompt, system)
