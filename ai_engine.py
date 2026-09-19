"""
CareOS AI engine  (Teammate 1)  -- Google Gemini version (free tier, no card needed)
------------------------------------------------------------------------------------
One public function is all the frontend needs:

    analyze_image(image_file, document_type, language) -> str

image_file    : file path (str), raw bytes, or a Streamlit UploadedFile
document_type : "prescription" or "lab_report" (also accepts "Prescription", "Lab Report")
language      : "English", "Hindi", "Tamil" or "Telugu"

Returns a Markdown string ready for st.markdown().
Raises AIEngineError with a human-friendly message if anything goes wrong.
"""
import io
import os
import time

from google import genai
from google.genai import types
from PIL import Image, ImageOps

try:  # loads GEMINI_API_KEY from a local .env file when running on your laptop
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Model names change over time. If one stops working, change it here or set GEMINI_MODEL in .env
MODELS = [m for m in [os.getenv("GEMINI_MODEL"), "gemini-2.5-flash", "gemini-2.5-flash-lite"] if m]
MAX_SIDE = 1600  # resize big phone photos -> faster uploads
SUPPORTED_LANGUAGES = ["English", "Hindi", "Tamil", "Telugu"]


class AIEngineError(Exception):
    """Raised with a message that is safe to show directly to the user.
    .details holds the technical reason (for developers / debugging)."""

    def __init__(self, message, details=""):
        super().__init__(message)
        self.details = details


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------
SYSTEM_PROMPT = """You are CareOS, a warm and careful healthcare assistant helping Indian families \
understand medical documents. The reader is a worried family caregiver, not a doctor.

Rules you must always follow:
- Use simple, calm, everyday words. No jargon. If you must use a medical term, explain it in brackets.
- Write the ENTIRE answer in {language}, using its native script. Keep medicine names, test names \
and numbers in English as well (e.g. "Paracetamol 500 mg") so a pharmacist can match them.
- NEVER diagnose a disease and NEVER tell the person to start, stop or change a medicine.
- If any handwriting or value is unclear, say "unclear - please confirm with the doctor or pharmacist". \
Never guess a medicine name or a dose.
- If the image is not a medical document, or is unreadable, say so briefly and ask for a clearer photo.
- Be concise. Use short bullet points."""

PRESCRIPTION_PROMPT = """You are a friendly pharmacist. Read this prescription image and explain it.

Use exactly these sections (translate the headings into {language}):

## Quick Summary
1-2 lines: what this prescription looks like it is for.

## Medicines
For EACH medicine:
- **Name** (as written)
- What it is for (in simple words)
- How to take it: dose, how many times a day, before/after food, for how many days
- Common side effects (2-3 only) and one simple tip

## Unclear Items
Anything you could not read confidently.

## Questions to Ask the Doctor
2-3 useful questions the caregiver should ask.

## Reminder
One line: this is an explanation, not medical advice - follow the doctor's instructions."""

REPORT_PROMPT = """You are a caring doctor explaining a lab report to a family member. \
Read this lab report image and explain it. Do NOT diagnose.

Use exactly these sections (translate the headings into {language}):

## Quick Summary
2 lines: overall picture in plain words.

## Values Outside the Normal Range
For EACH abnormal value:
- **Test name** - patient's value vs normal range - High/Low
- What this test measures and what a High/Low result can commonly mean, in simple words

If everything is normal, say so.

## Values in the Normal Range
One short line listing them.

## Questions to Ask the Doctor
2-3 useful questions the caregiver should ask.

## Reminder
One line: this is an explanation, not a diagnosis - please consult the doctor."""

PROMPTS = {"prescription": PRESCRIPTION_PROMPT, "lab_report": REPORT_PROMPT}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _get_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:  # fallback for Streamlit Cloud secrets
        try:
            import streamlit as st
            key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            key = None
    if not key:
        raise AIEngineError(
            "GEMINI_API_KEY not found. Put it in a .env file (local) or Streamlit secrets (deployed)."
        )
    return genai.Client(api_key=key)


def _read_bytes(image_file) -> bytes:
    if isinstance(image_file, (str, os.PathLike)):
        with open(image_file, "rb") as f:
            return f.read()
    if isinstance(image_file, (bytes, bytearray)):
        return bytes(image_file)
    if hasattr(image_file, "getvalue"):  # Streamlit UploadedFile
        return image_file.getvalue()
    if hasattr(image_file, "read"):
        return image_file.read()
    raise AIEngineError("Unsupported image input.")


def _prepare_image(image_file) -> bytes:
    """Fix phone rotation, shrink, and return JPEG bytes."""
    try:
        img = Image.open(io.BytesIO(_read_bytes(image_file)))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except AIEngineError:
        raise
    except Exception:
        raise AIEngineError("Could not open this image. Please upload a JPG or PNG photo.")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def _normalise_type(document_type: str) -> str:
    key = document_type.strip().lower().replace(" ", "_")
    if key not in PROMPTS:
        raise AIEngineError(f"Unknown document type '{document_type}'. Use 'prescription' or 'lab_report'.")
    return key


def _error_code(e):
    return getattr(e, "code", None) or getattr(e, "status_code", None)


def _discover_models(client, already_tried):
    """Ask Google which models this key can actually use, newest 'flash' models first."""
    try:
        found = []
        for m in client.models.list():
            name = m.name.replace("models/", "")
            actions = getattr(m, "supported_actions", None) or []
            if "flash" not in name or (actions and "generateContent" not in actions):
                continue
            if any(bad in name for bad in ("image", "tts", "live", "audio", "embedding", "thinking", "robotics")):
                continue
            if name not in already_tried:
                found.append(name)
        # stable, non-lite, highest version first; preview/lite last
        found.sort(key=lambda n: (("preview" in n or "exp" in n), ("lite" in n), _neg(n)))
        return found[:4]
    except Exception:
        return []


def _neg(name):
    return tuple(-ord(c) for c in name)  # sort names in descending order


def _generate(client, models, contents, config):
    """Try each model in turn. Returns (text_or_None, last_error, model_used)."""
    last_error = None
    for model in models:
        for attempt in range(3):  # free tier has low per-minute limits -> retry on 429
            try:
                resp = client.models.generate_content(model=model, contents=contents, config=config)
                if resp.text:
                    return resp.text, None, model
                raise AIEngineError("The AI returned an empty answer. Please try a clearer photo.")
            except AIEngineError:
                raise
            except Exception as e:
                last_error = e
                code = _error_code(e)
                if code == 429:
                    time.sleep(6 * (attempt + 1))
                    continue
                if code in (400, 401, 403) and "API key" in str(e):
                    raise AIEngineError("The Gemini API key is invalid. Check GEMINI_API_KEY.", details=str(e))
                break  # model not found / other error -> try the next model
    return None, last_error, None


# --------------------------------------------------------------------------
# Public function
# --------------------------------------------------------------------------
def analyze_image(image_file, document_type: str, language: str = "English") -> str:
    doc_key = _normalise_type(document_type)
    if language not in SUPPORTED_LANGUAGES:
        language = "English"

    jpeg = _prepare_image(image_file)
    client = _get_client()

    contents = [
        types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
        PROMPTS[doc_key].format(language=language),
    ]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT.format(language=language),
        temperature=0.2,  # low = consistent, fewer made-up details
    )

    text, last_error, used = _generate(client, MODELS, contents, config)
    if text:
        return text

    # Configured models failed (often: model retired / renamed). Ask Google what is available.
    if _error_code(last_error) in (400, 404):
        extra = _discover_models(client, MODELS)
        if extra:
            text, err2, used = _generate(client, extra, contents, config)
            if text:
                print(f"[CareOS] Using auto-discovered model: {used}  (put GEMINI_MODEL={used} in .env to make it permanent)")
                return text
            last_error = err2 or last_error

    details = f"{type(last_error).__name__}: {str(last_error)[:400]}"
    if _error_code(last_error) == 429:
        raise AIEngineError("Too many requests right now (free-tier limit). Wait a minute and try again.", details=details)
    raise AIEngineError(f"The AI service had a problem ({type(last_error).__name__}). Please try again.", details=details)
