"""The single, configuration-driven gateway for Nyaya Mitra model calls.

Every response reports the provider that actually generated it.  If no model is
available, the gateway returns only a review-required operational notice; it
never substitutes pre-written legal advice or translations for an AI response.
"""

from __future__ import annotations

import os
from typing import Callable

import requests
from dotenv import load_dotenv
from groq import Groq

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
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    if not api_key:
        raise RuntimeError("Groq requires GROQ_API_KEY")
    completion = Groq(api_key=api_key).chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        timeout=float(os.getenv("GROQ_TIMEOUT_SECONDS", "15")),
    )
    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("Groq response did not contain generated text")
    return content


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
