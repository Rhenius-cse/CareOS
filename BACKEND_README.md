# 🩺 CareOS: The Caregiver's Command Center

> Snap a photo of a prescription or lab report. CareOS explains it in plain language, in **English, Hindi, Tamil or Telugu**, and tells you what to ask the doctor.

Built for **Celestia 2.0** (Unstop hackathon) · Track: **Healthcare**

| | |
|---|---|
| 🎨 Design (Figma) | `<add Figma link>` |
| 🌐 Live demo | `<add Streamlit URL>` |
| 🎥 Demo video | `<add link>` |
| 📊 Presentation | `<add link>` |

---

## The problem

In India, when a parent falls sick, the whole family scrambles. Prescriptions are hard to read, lab reports are full of medical jargon, and relatives often don't know who has already given which medicine. That leads to confusion, missed questions at the doctor's office, and the risk of **accidental double-dosing**.

## The solution

CareOS is a multilingual, AI-powered command center for family healthcare.

- 📸 **Snap and understand.** Upload a photo of a prescription or lab report.
- 🗣️ **Your language.** The explanation comes back in simple English, Hindi, Tamil or Telugu.
- 🚩 **Highlights what matters.** Abnormal lab values are flagged, and unclear handwriting is marked "unclear" instead of guessed.
- ❓ **Questions for the doctor.** Every result ends with suggested questions to ask.
- 👨‍👩‍👧 **Shared Family Log.** When one person gives a dose, the whole family can see it, preventing double-dosing.

---

## Features and status

| Feature | Status |
|---|---|
| Prescription explainer (image → plain language) | ✅ Working |
| Lab report explainer (flags abnormal values) | ✅ Working |
| Languages: English, Hindi, Tamil, Telugu | ✅ Working (quality being tuned) |
| Streamlit web UI | 🔧 In progress |
| Shared Family Log (Google Sheets) | 🔧 In progress |
| Live ER wait times / hospitals tab | 🗓️ Planned |
| Pharmacy integration | 🗓️ Planned |

---

## How it works

```
 Photo upload ──► Streamlit UI (app.py)
                       │
                       ▼
              ai_engine.py  ── cleans the image (fix rotation, resize)
                       │       builds the prompt (pharmacist / doctor role + language)
                       ▼
               Google Gemini (vision)
                       │
                       ▼
        Plain-language explanation ──► shown in the UI
```

The engine exposes one function:

```python
from ai_engine import analyze_image, AIEngineError

try:
    text = analyze_image(uploaded_file, "prescription", "Hindi")
    # document_type: "prescription" or "lab_report"
    # language: "English", "Hindi", "Tamil", "Telugu"
    print(text)
except AIEngineError as e:
    print("Something went wrong:", e)
```

**Built-in safeguards**
- Never diagnoses and never tells the user to start, stop or change a medicine.
- Marks unreadable handwriting or values as "unclear" instead of guessing.
- Keeps medicine and test names in English as well, so a pharmacist can match them.
- Every result ends with a reminder to follow the doctor's instructions.
- Retries automatically when the API rate limit is reached, and falls back to another Gemini model if one is unavailable.

---

## Tech stack

- **Python 3.10+**
- **Streamlit** for the web interface
- **Google Gemini API** (`google-genai`) for vision and language
- **Pillow** for image preparation
- **python-dotenv** for local configuration
- **Google Sheets** (`gspread`) for the shared Family Log

---

## Project structure

```
CareOS/
├── app.py             # Streamlit UI
├── ai_engine.py       # AI brain: image + language → explanation
├── test_ai.py         # Command-line tester for the AI engine
├── check_key.py       # Diagnoses API key problems (never prints the key)
├── requirements.txt   # Python dependencies
├── .env.example       # Template for your secret key
└── .gitignore         # Keeps secrets and junk out of Git
```

---

## Run it locally

**1. Clone the repo and open the folder**
```bash
git clone <this-repo-url>
cd CareOS
```

**2. Create and activate a virtual environment**

Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\activate
```
Mac / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
python -m pip install -r requirements.txt
```

**4. Add your free Gemini API key**

Get a key (no credit card) at <https://aistudio.google.com/apikey>. Then:

Windows: `Copy-Item .env.example .env`  ·  Mac/Linux: `cp .env.example .env`

Open `.env` and put your key on the `GEMINI_API_KEY=` line, with no spaces or quotes. Never commit this file.

**5. Verify the key**
```bash
python check_key.py
```
You should see `SUCCESS: Google accepted your key.`

**6. Try the AI engine from the terminal**
```bash
python test_ai.py path/to/prescription.jpg --type prescription --lang Hindi
python test_ai.py path/to/report.jpg --type lab_report --lang Tamil
```
Results are also saved to a `test_outputs/` folder.

**7. Run the app**
```bash
streamlit run app.py
```

### Deploying on Streamlit Cloud
Add this under **App settings → Secrets** (do not put the key in the code):
```toml
GEMINI_API_KEY = "your-key-here"
```

### Optional settings (in `.env`)
| Variable | Purpose |
|---|---|
| `GEMINI_MODEL` | Force a specific Gemini model if the default stops working |
| `GEMINI_THINKING_BUDGET` | Cap the model's reasoning time for faster answers (e.g. `512`) |

---

## ⚠️ Important notes

- **CareOS is an explanation tool, not medical advice.** It does not diagnose. Always follow your doctor's and pharmacist's instructions.
- **AI can make mistakes**, especially with messy handwriting. Always confirm important details, such as medicine names and doses, with a doctor or pharmacist.
- **Privacy:** this prototype uses the free Gemini tier, where inputs may be used by Google to improve its products. Use only sample or fake documents, never real patient records, until a production-grade setup is in place.

---

## Roadmap

1. Hospital tab with live ER wait times
2. Pharmacy integration and medicine reminders
3. More Indian languages (Marathi, Bengali, Kannada, Malayalam)
4. Family accounts with access control
5. Privacy-first production setup for real medical documents

---

## Team

| Name | Role |
|---|---|
| `<name>` | AI & Backend |
| `<name>` | Frontend & UI |
| `<name>` | Integration, QA & Deployment |
| `<name>` | Pitch & Storytelling |

*Built with ❤️ for the families who hold everything together.*
