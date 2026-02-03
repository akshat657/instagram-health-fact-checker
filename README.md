# 🔍 Instagram Health Fact-Checker

AI-powered tool to detect health misinformation in Instagram Reels. Uses multiple scientific databases and Llama 3 for accurate fact-checking.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## ✨ Features

- 🎥 **Instagram Reel Download** - Paste any reel URL
- 🎙️ **Speech-to-Text** - Whisper AI transcription
- 🌐 **Multi-language** - Hindi, Urdu, English support (auto-translates to English)
- 🔬 **6 Evidence Sources**:
  - PubMed (Scientific Papers)
  - Semantic Scholar (200M+ Research Papers)
  - ClinicalTrials.gov (Clinical Trials)
  - OpenAlex (250M+ Academic Works)
  - Google Fact Check API
  - Built-in Health Database (WHO, FDA, IARC)
- 🤖 **Llama 3 Analysis** - Intelligent verdict generation
- 💬 **Chat Feature** - Ask questions about the video

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/instagram-health-fact-checker.git
cd instagram-health-fact-checker
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

Create `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key
GOOGLE_FACT_CHECK_API_KEY=your_google_key
DATABASE_URL=sqlite:///./fact_checker.db
WHISPER_MODEL=base
```

### 5. Run the App

```bash
streamlit run app/streamlit_app.py --server.port 8501
```

Open: http://localhost:8501

## 📁 Project Structure

```
instagram-health-fact-checker/
├── app/
│   └── streamlit_app.py      # Main Streamlit UI
├── utils/
│   ├── instagram_handler.py   # Download & transcribe reels
│   ├── claim_extractor.py     # Extract health claims
│   ├── evidence_finder.py     # Multi-source evidence search
│   ├── fact_checker.py        # Llama 3 verification
│   ├── pubmed_api.py          # PubMed API
│   ├── transcript_corrector.py # Fix transcription errors
│   └── database.py            # SQLite storage
├── requirements.txt
├── .env.example
└── README.md
```

## 🔑 API Keys (All FREE!)

| API | Get Key | Required |
|-----|---------|----------|
| Groq (Llama 3) | [console.groq.com](https://console.groq.com) | ✅ Yes |
| Semantic Scholar | [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) | ⚪ Optional |
| Google Fact Check | [console.cloud.google.com](https://console.cloud.google.com) | ⚪ Optional |

## 📊 How It Works

```
Instagram Reel URL
       ↓
📥 Download Video (Instaloader)
       ↓
🎙️ Transcribe Audio (Whisper)
       ↓
🔄 Translate to English (Llama 3)
       ↓
📋 Extract Health Claims (Llama 3)
       ↓
🔍 Search Evidence (6 Sources)
       ↓
⚖️ Verify Each Claim (Llama 3)
       ↓
📊 Display Results with Sources
```

## 🎯 Verdict Types

| Verdict | Meaning |
|---------|---------|
| ✅ TRUE | Claim supported by evidence |
| ❌ FALSE | Claim contradicts evidence |
| ⚠️ MIXED | Partially true/false |
| ❓ UNVERIFIED | Insufficient evidence |

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **LLM**: Llama 3.3 70B (via Groq)
- **Speech-to-Text**: OpenAI Whisper
- **Database**: SQLite / PostgreSQL
- **APIs**: PubMed, Semantic Scholar, OpenAlex, ClinicalTrials.gov

## 📝 License

MIT License - feel free to use and modify!

## 🤝 Contributing

Pull requests welcome! For major changes, open an issue first.

## ⚠️ Disclaimer

This tool is for educational purposes. Always consult healthcare professionals for medical advice.