"""
Streamlit Web Application for Instagram Health Claim Fact-Checker
Using Google Gemini (FREE!)
"""

import os
import sys
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Page configuration
st.set_page_config(
    page_title="Health Claim Fact-Checker",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Robust Import Handling
try:
    from utils.instagram_handler import InstagramHandler
    from utils.fact_checker import FactChecker
    from utils.database import Database
except ImportError as e:
    st.error(f"Import error: {e}")
    st.info("Check if utils folder exists and contains __init__.py")
    st.stop()

# --- STYLING ---
st.markdown("""
<style>
    .claim-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        border-left: 4px solid #007bff;
        color: #1f1f1f;
    }
    .rating-badge {
        display: inline-block;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        margin: 5px;
    }
    .rating-true { background-color: #d4edda; color: #155724; }
    .rating-false { background-color: #f8d7da; color: #721c24; }
    .rating-mixed { background-color: #fff3cd; color: #856404; }
    .rating-unverified { background-color: #e2e3e5; color: #383d41; }
</style>
""", unsafe_allow_html=True)

# --- UTILS ---
def get_verdict_emoji(verdict: str) -> str:
    emojis = {
        "TRUE": "✅", "FALSE": "❌", "MIXED": "⚠️", "UNVERIFIED": "❓",
        "MOSTLY_TRUE": "✅", "MOSTLY_FALSE": "❌", "NO_CLAIMS": "ℹ️"
    }
    return emojis.get(verdict.upper(), "❓")

def get_verdict_color(verdict: str) -> str:
    colors = {
        "TRUE": "true", "FALSE": "false", "MIXED": "mixed",
        "UNVERIFIED": "unverified", "MOSTLY_TRUE": "true", "MOSTLY_FALSE": "false"
    }
    return colors.get(verdict.upper(), "unverified")

@st.cache_resource
def get_database():
    return Database()

@st.cache_resource
def get_fact_checker():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return FactChecker(api_key=api_key)

@st.cache_resource
def get_instagram_handler():
    model_name = os.getenv("WHISPER_MODEL", "base")
    return InstagramHandler(whisper_model=model_name)

# --- UI COMPONENTS ---
def display_verdict_card(verdict, index: int):
    emoji = get_verdict_emoji(verdict.verdict)
    color = get_verdict_color(verdict.verdict)
    
    st.markdown(f"""
    <div class="claim-card">
        <h4>{emoji} Claim #{index + 1}</h4>
        <p><strong>"{verdict.claim}"</strong></p>
        <p>
            <span class="rating-badge rating-{color}">
                {verdict.verdict} ({verdict.confidence:.0%} confidence)
            </span>
            <span style="color: #666; font-size: 0.9em;">
                Category: {verdict.category}
            </span>
        </p>
        <p><strong>Analysis:</strong> {verdict.explanation}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if verdict.sources:
        with st.expander(f"📚 View {len(verdict.sources)} Scientific Sources"):
            for source in verdict.sources:
                st.markdown(f"- [{source}]({source})")

# --- MAIN APP ---
def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("⚠️ GROQ_API_KEY not set!")
        st.markdown("Get FREE key at [console.groq.com](https://console.groq.com/)")
        st.stop()

    # Sidebar
    with st.sidebar:
        st.title("🏥 Health Fact-Checker")
        st.markdown("*Powered by Google Gemini*")
        st.divider()
        
        language = st.selectbox(
            "🌐 Transcription Language",
            options=list(InstagramHandler.SUPPORTED_LANGUAGES.keys()),
            index=1,
            format_func=str.title
        )
        
        st.divider()
        st.subheader("📜 Recent Checks")
        try:
            db = get_database()
            history = db.get_recent_fact_checks(limit=5)
            if history:
                for item in history:
                    st.write(f"{get_verdict_emoji(item.get('overall_rating', ''))} {item.get('shortcode', 'Reel')[:10]}...")
            else:
                st.info("No history yet.")
        except:
            st.caption("History unavailable")

    st.title("🔍 Instagram Health Fact-Checker")
    url = st.text_input("📎 Paste Instagram Reel URL", placeholder="https://www.instagram.com/reel/...")

    if st.button("🔍 Check Claims", type="primary") and url:
        try:
            handler = get_instagram_handler()
            fact_checker = get_fact_checker()
            db = get_database()

            with st.status("🚀 Processing...", expanded=True) as status:
                st.write("📥 Downloading audio...")
                video_info = handler.process_reel(url, language)
                
                st.write("📝 Transcribing...")
                st.info(f"Preview: {video_info['transcript'][:200]}...")
                
                st.write("🔬 Fact-checking with Gemini...")
                result = fact_checker.check_claims(video_info["transcript"], url, language)
                
                st.write("💾 Archiving...")
                result_dict = fact_checker.to_dict(result)
                record_id = db.save_fact_check(result_dict)
                
                status.update(label="✅ Analysis Complete!", state="complete")

            st.session_state.current_result = result
            st.session_state.current_result_id = record_id
            st.session_state.current_transcript = video_info["transcript"]
            
            # Cleanup temp files
            video_path = video_info.get("video_path")
            if video_path:
                handler.cleanup(video_path)

        except Exception as e:
            st.error(f"Error: {e}")

    # Display Results Logic
    if st.session_state.get("current_result"):
        res = st.session_state.current_result
        st.divider()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Rating", res.overall_rating)
        c2.metric("Confidence", f"{res.overall_confidence:.0%}")
        c3.metric("Claims", res.claims_found)
        
        t1, t2, t3 = st.tabs(["📋 Analysis", "📝 Transcript", "💬 Ask Questions"])
        with t1:
            for i, v in enumerate(res.verdicts):
                display_verdict_card(v, i)
        with t2:
            st.text_area("Raw Text", value=st.session_state.current_transcript, height=300)
        with t3:
            q = st.text_input("Ask about this video:")
            if q:
                fc = get_fact_checker()
                if fc:
                    ans = fc.chat_about_video(q, res)
                    st.chat_message("assistant").write(ans)

if __name__ == "__main__":
    main()