"""
Language model calls with a fixed fallback order: OpenAI, then Gemini, then Claude.
A provider is skipped when it has no key, errors, times out, or returns something unusable.
Only the minimum context is sent: no names, emails or account ids.
"""
import json
import logging
import re

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class ProviderError(Exception):
    pass


def _openai(system, prompt, json_mode, max_tokens):
    body = {
        "model": settings.OPENAI_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = requests.post("https://api.openai.com/v1/chat/completions", json=body, timeout=settings.LLM_TIMEOUT_SECONDS,
                      headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"})
    if r.status_code >= 300:
        raise ProviderError(f"openai {r.status_code}: {r.text[:200]}")
    return r.json()["choices"][0]["message"]["content"]


def _gemini(system, prompt, json_mode, max_tokens):
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.4},
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
    r = requests.post(url, json=body, timeout=settings.LLM_TIMEOUT_SECONDS,
                      headers={"x-goog-api-key": settings.GEMINI_API_KEY})
    if r.status_code >= 300:
        raise ProviderError(f"gemini {r.status_code}: {r.text[:200]}")
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _anthropic(system, prompt, json_mode, max_tokens):
    body = {
        "model": settings.ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "system": system + ("\nReply with a single JSON object and nothing else." if json_mode else ""),
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post("https://api.anthropic.com/v1/messages", json=body, timeout=settings.LLM_TIMEOUT_SECONDS,
                      headers={"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"})
    if r.status_code >= 300:
        raise ProviderError(f"anthropic {r.status_code}: {r.text[:200]}")
    return "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")


def providers():
    out = []
    if settings.OPENAI_API_KEY:
        out.append(("openai", _openai))
    if settings.GEMINI_API_KEY:
        out.append(("gemini", _gemini))
    if settings.ANTHROPIC_API_KEY:
        out.append(("claude", _anthropic))
    return out


def status():
    names = [n for n, _ in providers()]
    return {"providers": names, "voice": bool(settings.OPENAI_API_KEY)}


def clean_text(text):
    text = (text or "").strip()
    return text.replace("\u2014", "-").replace("\u2013", "-")


def _parse_json(text):
    text = (text or "").strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no json object")
    return json.loads(text[start:end + 1])


def complete(system, prompt, max_tokens=500, validate=None):
    """Plain text. Returns (text, provider) or (None, None) when every provider fails."""
    for name, fn in providers():
        try:
            text = clean_text(fn(system, prompt, False, max_tokens))
            if not text or (validate and not validate(text)):
                raise ProviderError("empty or invalid answer")
            return text, name
        except (requests.RequestException, ProviderError, KeyError, IndexError, ValueError) as exc:
            log.warning("Provider %s failed, trying next: %s", name, exc)
    return None, None


def complete_json(system, prompt, max_tokens=500, validate=None):
    for name, fn in providers():
        try:
            data = _parse_json(fn(system, prompt, True, max_tokens))
            if validate and not validate(data):
                raise ProviderError("json failed validation")
            return data, name
        except (requests.RequestException, ProviderError, KeyError, IndexError, ValueError) as exc:
            log.warning("Provider %s failed for JSON, trying next: %s", name, exc)
    return None, None


def transcribe(file_obj, filename="voice.webm"):
    if not settings.OPENAI_API_KEY:
        raise ProviderError("Voice needs an OpenAI key on the server.")
    r = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
        files={"file": (filename, file_obj, "application/octet-stream")},
        data={"model": settings.OPENAI_TRANSCRIBE_MODEL, "language": "en",
              "prompt": "Health diary. Words like acidity, Pepcid, Tylenol, Advil, Gravol, Tums, cramps, migraine."},
        timeout=60,
    )
    if r.status_code >= 300:
        raise ProviderError(f"transcription failed: {r.status_code} {r.text[:200]}")
    return r.json().get("text", "").strip()
