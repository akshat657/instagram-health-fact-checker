# 🏥 Health Claim Fact-Checker Pro

AI-powered fact-checker for health claims in Instagram Reels using Llama 3.3 AI and medical databases.

## ✨ Features

- 🎥 Download & transcribe Instagram Reels
- 🧠 AI-powered claim extraction (Llama 3.3)
- 🔬 Multi-source verification (PubMed, WHO, FDA, NIH, OpenAlex)
- 🌍 Multi-language support (Hindi, English, Urdu, etc.)
- 📊 Beautiful visualizations
- 💬 Ask questions about videos
- 📄 Export PDF/HTML reports
- 💾 Smart caching
- 🗄️ Database for history

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg

**Windows:**
```bash
winget install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

### 3. Setup API Key

Create `.env` file:
```env
GROQ_API_KEY=your_key_here
```

Get FREE API key at: https://console.groq.com/

### 4. Run
```bash
streamlit run app/streamlit_app.py
```

## 📖 How It Works

1. **Download**: Downloads Instagram Reel audio
2. **Transcribe**: Whisper AI converts speech to text
3. **Correct**: Llama AI fixes transcription errors
4. **Extract**: Identifies all health claims
5. **Verify**: Searches 10+ medical databases
6. **Analyze**: AI evaluates evidence
7. **Report**: Generates detailed fact-check

## 🔍 Evidence Sources

- **PubMed** - Peer-reviewed research
- **ClinicalTrials.gov** - Clinical trials
- **OpenAlex** - 250M+ papers
- **Semantic Scholar** - Citation data
- **WHO, FDA, NIH** - Authoritative sources
- **Built-in** - Medical facts database

## 📊 Project Structure
```
health-factchecker/
├── app/
│   └── streamlit_app.py      # Main Streamlit app
├── models/
│   └── schemas.py             # Pydantic schemas
├── utils/
│   ├── instagram_handler.py   # Download & transcribe
│   ├── claim_extractor.py     # Extract claims
│   ├── fact_checker.py        # Verify claims
│   ├── evidence_finder.py     # Search databases
│   ├── transcript_corrector.py # Fix errors
│   ├── pubmed_api.py          # PubMed integration
│   ├── database.py            # SQLite/PostgreSQL
│   ├── report_generator.py    # PDF/HTML export
│   └── creator_checker.py     # Creator credibility
├── .env                       # API keys
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

## 🎯 Usage Examples

### Basic Usage
```python
from utils.fact_checker import FactChecker

fc = FactChecker(api_key="your_groq_key")
result = fc.check_claims(
    transcript="Eating burnt roti causes cancer",
    url="https://instagram.com/reel/..."
)
```

### With Instagram Handler
```python
from utils.instagram_handler import InstagramHandler

handler = InstagramHandler()
video_info = handler.process_reel(
    url="https://instagram.com/reel/...",
    language="hindi"
)
```

## 🛠️ Configuration

### Environment Variables
```env
# Required
GROQ_API_KEY=your_key

# Optional (for higher rate limits)
NCBI_API_KEY=
SEMANTIC_SCHOLAR_API_KEY=
GOOGLE_FACT_CHECK_API_KEY=

# Whisper model (base/small/medium/large)
WHISPER_MODEL=base

# Database
DATABASE_URL=sqlite:///./fact_checker.db
```

## 🌐 Supported Languages

Hindi, English, Urdu, Punjabi, Bengali, Tamil, Telugu, Marathi, Gujarati, Spanish, French, German, Arabic, Mandarin, Japanese, Korean, Portuguese, Italian, Russian

## 📝 License

MIT License - Feel free to use for any purpose

## 🤝 Contributing

Contributions welcome! Open issues or PRs.

## ⚠️ Disclaimer

This tool is for informational purposes only. Not a substitute for professional medical advice. Always consult healthcare professionals.

## 🙏 Acknowledgments

- Groq (Llama 3.3)
- OpenAI (Whisper)
- NCBI (PubMed)
- Instaloader
- Streamlit

## 📧 Support

For issues: [Open an issue](https://github.com/yourusername/health-factchecker/issues)
```
