"""Diagnoses API-key problems WITHOUT printing your key.  Run:  python check_key.py"""
import os

# 1) Was a key already set in Windows itself? (it would silently beat the .env file)
for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
    if os.environ.get(name):
        print(f"WARNING: {name} is already set in your Windows environment "
              f"(length {len(os.environ[name])}). It can override .env!")

# 2) Load .env
from dotenv import load_dotenv
found = load_dotenv()
print(".env file found:", found)

key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
print("Key length:", len(key), "(Gemini keys are usually 39)")
if not key:
    raise SystemExit("PROBLEM: no key loaded. Is the file named exactly .env and saved in this folder?")
print("Starts with:", key[:4], "| Ends with:", key[-2:])

if "paste" in key.lower() or "your" in key.lower():
    print("PROBLEM: this is still the placeholder text, not your real key.")
if key != key.strip() or " " in key:
    print("PROBLEM: the key contains a space.")
if key[0] in "\"'" or key[-1] in "\"'":
    print("PROBLEM: remove the quote marks around the key.")
if not key.startswith("AIza"):
    print("NOTE: Gemini keys normally start with AIza. Recopy from aistudio.google.com/apikey")

# 3) Live check with Google (free, just lists models)
try:
    from google import genai
    client = genai.Client(api_key=key)
    names = [m.name for m in client.models.list()]
    print("\nSUCCESS: Google accepted your key.")
    print("Some available models:", [n for n in names if "flash" in n][:6])
except Exception as e:
    print("\nGoogle rejected the request:", type(e).__name__, "-", str(e)[:200])
