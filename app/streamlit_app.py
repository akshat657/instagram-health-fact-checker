"""
Enhanced Streamlit Web Application for Instagram Health Claim Fact-Checker
With visualizations, PDF export, and advanced features
"""

import os
import sys
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import hashlib

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Page configuration
st.set_page_config(
    page_title="Health Claim Fact-Checker Pro",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Robust Import Handling
try:
    from utils.instagram_handler import InstagramHandler
    from utils.fact_checker import FactChecker
    from utils.database import Database
    from utils.report_generator import ReportGenerator
    from utils.creator_checker import CreatorCredibilityChecker
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
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    
    .educational-box {
        background-color: #e7f3ff;
        border-left: 4px solid #2196F3;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
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

@st.cache_resource
def get_report_generator():
    return ReportGenerator()

@st.cache_resource
def get_creator_checker():
    return CreatorCredibilityChecker()

# --- VISUALIZATION COMPONENTS ---
def display_evidence_quality_chart(verdicts):
    """Visual breakdown of evidence quality"""
    if not verdicts:
        return
    
    # Count evidence sources
    sources = {}
    for v in verdicts:
        for evidence in v.evidence:
            source = evidence.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
    
    if not sources:
        st.info("No evidence sources to display")
        return
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(sources.keys()),
            y=list(sources.values()),
            marker_color='lightblue',
            text=list(sources.values()),
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Evidence Sources Distribution",
        xaxis_title="Source",
        yaxis_title="Number of Evidence Pieces",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_confidence_chart(verdicts):
    """Show confidence levels across claims"""
    if not verdicts:
        return
    
    claims = [f"Claim {i+1}" for i in range(len(verdicts))]
    confidences = [v.confidence * 100 for v in verdicts]
    verdicts_text = [v.verdict for v in verdicts]
    
    # Color by verdict
    colors = []
    for v in verdicts:
        if v.verdict in ["TRUE", "MOSTLY_TRUE"]:
            colors.append('green')
        elif v.verdict in ["FALSE", "MOSTLY_FALSE"]:
            colors.append('red')
        elif v.verdict == "MIXED":
            colors.append('orange')
        else:
            colors.append('gray')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=claims,
        y=confidences,
        marker_color=colors,
        text=[f"{c:.1f}%" for c in confidences],
        textposition='auto',
        hovertext=[f"{claims[i]}<br>Verdict: {verdicts_text[i]}<br>Confidence: {confidences[i]:.1f}%" 
                   for i in range(len(claims))],
        hoverinfo='text'
    ))
    
    fig.update_layout(
        title="Confidence Levels by Claim",
        xaxis_title="Claim",
        yaxis_title="Confidence (%)",
        height=400,
        yaxis_range=[0, 100]
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_verdict_distribution(verdicts):
    """Pie chart of verdict distribution"""
    if not verdicts:
        return
    
    verdict_counts = {}
    for v in verdicts:
        verdict_counts[v.verdict] = verdict_counts.get(v.verdict, 0) + 1
    
    fig = go.Figure(data=[go.Pie(
        labels=list(verdict_counts.keys()),
        values=list(verdict_counts.values()),
        hole=.3,
        marker_colors=['green', 'red', 'orange', 'gray']
    )])
    
    fig.update_layout(
        title="Verdict Distribution",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_category_breakdown(verdicts):
    """Show claims by category"""
    if not verdicts:
        return
    
    categories = {}
    for v in verdicts:
        cat = v.category
        categories[cat] = categories.get(cat, 0) + 1
    
    fig = go.Figure(data=[
        go.Bar(
            y=list(categories.keys()),
            x=list(categories.values()),
            orientation='h',
            marker_color='lightcoral',
            text=list(categories.values()),
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title="Claims by Health Category",
        xaxis_title="Number of Claims",
        yaxis_title="Category",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

# --- UI COMPONENTS ---
def display_verdict_card(verdict, index: int):
    emoji = get_verdict_emoji(verdict.verdict)
    color = get_verdict_color(verdict.verdict)
    
    st.markdown(f"""
    <div class="claim-card">
        <h4>{emoji} Claim #{index + 1}</h4>
        <p><strong>Original:</strong> "{verdict.claim}"</p>
        {f'<p><strong>English:</strong> "{verdict.claim_english}"</p>' if verdict.claim != verdict.claim_english else ''}
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
            for i, source in enumerate(verdict.sources[:10], 1):
                st.markdown(f"{i}. [{source}]({source})")
    
    if verdict.evidence:
        with st.expander(f"🔬 View {len(verdict.evidence)} Evidence Pieces"):
            for i, ev in enumerate(verdict.evidence[:5], 1):
                st.markdown(f"""
                **{i}. {ev.get('source', 'Unknown').upper()}**  
                *{ev.get('title', 'No title')}*  
                [Link]({ev.get('url', '#')})
                """)

def show_educational_sidebar():
    """Educational content for users"""
    with st.sidebar.expander("🎓 How to Spot Health Misinformation"):
        st.markdown("""
        ### ⚠️ Red Flags:
        - ✗ Claims of "miracle cures"
        - ✗ Dismisses all mainstream medicine
        - ✗ No sources cited
        - ✗ Relies on anecdotes only
        - ✗ Creates fear/urgency
        - ✗ Promotes expensive products
        - ✗ "Doctors don't want you to know"
        
        ### ✅ Green Flags:
        - ✓ Cites peer-reviewed research
        - ✓ Acknowledges limitations
        - ✓ Recommends consulting professionals
        - ✓ Balanced, nuanced claims
        - ✓ Transparent about conflicts of interest
        - ✓ Published in reputable journals
        """)
        
    with st.sidebar.expander("📊 Source Credibility Guide"):
        st.markdown("""
        **Most Reliable (🏆):**
        - Cochrane Reviews
        - WHO, CDC, FDA, NIH
        - Peer-reviewed medical journals
        - Systematic reviews & meta-analyses
        
        **Moderately Reliable (✅):**
        - University research
        - Medical news sites (WebMD, Mayo)
        - Clinical trials
        
        **Less Reliable (⚠️):**
        - Preprint servers (not peer-reviewed)
        - Personal blogs
        - News articles (secondary sources)
        
        **Not Reliable (❌):**
        - Social media influencers
        - Supplement company blogs
        - Testimonials & anecdotes
        - Anonymous sources
        """)

def display_contradiction_warnings(result):
    """Check for contradictions within the video"""
    contradictions = []
    
    # Simple contradiction check
    for i, v1 in enumerate(result.verdicts):
        for j, v2 in enumerate(result.verdicts[i+1:], i+1):
            # If one claim says TRUE and another says FALSE about similar topics
            if (v1.verdict in ["TRUE", "MOSTLY_TRUE"] and 
                v2.verdict in ["FALSE", "MOSTLY_FALSE"] and
                v1.category == v2.category):
                contradictions.append((i+1, j+1, v1.claim, v2.claim))
    
    if contradictions:
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.warning("⚠️ **Potential Contradictions Detected in Video**")
        for c in contradictions:
            st.markdown(f"""
            - Claim #{c[0]} and Claim #{c[1]} may contradict each other:
              - Claim #{c[0]}: *{c[2][:80]}...*
              - Claim #{c[1]}: *{c[3][:80]}...*
            """)
        st.markdown('</div>', unsafe_allow_html=True)

# --- MAIN APP ---
def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("⚠️ GROQ_API_KEY not set!")
        st.markdown("Get FREE key at [console.groq.com](https://console.groq.com/)")
        st.code("1. Sign up at console.groq.com\n2. Get your API key\n3. Add to .env file:\n   GROQ_API_KEY=your_key_here")
        st.stop()

    # Sidebar
    with st.sidebar:
        st.title("🏥 Health Fact-Checker Pro")
        st.markdown("*Powered by Llama 3.3 & Medical Databases*")
        st.divider()
        
        language = st.selectbox(
            "🌐 Transcription Language",
            options=list(InstagramHandler.SUPPORTED_LANGUAGES.keys()),
            index=1,
            format_func=str.title
        )
        
        st.divider()
        
        # Show educational content
        show_educational_sidebar()
        
        st.divider()
        st.subheader("📜 Recent Checks")
        try:
            db = get_database()
            history = db.get_recent_fact_checks(limit=5)
            if history:
                for item in history:
                    emoji = get_verdict_emoji(item.get('overall_rating', ''))
                    shortcode = item.get('shortcode', 'Reel')[:10]
                    claims = item.get('claims_found', 0)
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.caption(f"{emoji} {shortcode}...")
                    with col2:
                        st.caption(f"{claims} claims")
            else:
                st.info("No history yet.")
        except Exception as e:
            st.caption(f"History unavailable: {e}")

    # Main content
    st.title("🔍 Instagram Health Fact-Checker Pro")
    st.markdown("*Verify health claims from Instagram Reels using AI + medical databases*")
    
    # Input section
    col1, col2 = st.columns([4, 1])
    with col1:
        url = st.text_input(
            "📎 Paste Instagram Reel URL", 
            placeholder="https://www.instagram.com/reel/...",
            help="Enter the full URL of an Instagram Reel to fact-check"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        check_button = st.button("🔍 Check Claims", type="primary", use_container_width=True)

    # Process button click
    if check_button and url:
        try:
            handler = get_instagram_handler()
            fact_checker = get_fact_checker()
            db = get_database()
            
            # Check if already analyzed
            existing = db.get_fact_check_by_url(url)
            if existing:
                st.info("ℹ️ This video was previously analyzed. Showing cached results...")
                st.session_state.current_result = fact_checker.dict_to_result(existing)
                st.session_state.current_result_id = existing['id']
                st.session_state.current_transcript = existing['transcript']
                st.rerun()

            with st.status("🚀 Processing Reel...", expanded=True) as status:
                # Download & transcribe
                st.write("📥 Downloading audio...")
                video_info = handler.process_reel(url, language)
                
                st.write("📝 Transcribing...")
                transcript_preview = video_info['transcript'][:200]
                st.info(f"Preview: {transcript_preview}...")
                
                # Check creator credibility
                st.write("👤 Checking creator credibility...")
                creator_checker = get_creator_checker()
                shortcode = handler.extract_shortcode(url)
                
                # Fact-check
                st.write("🔬 Fact-checking claims with AI + Medical Databases...")
                result = fact_checker.check_claims(video_info["transcript"], url, language)
                
                # Save to database
                st.write("💾 Saving results...")
                result_dict = fact_checker.to_dict(result)
                record_id = db.save_fact_check(result_dict)
                
                status.update(label="✅ Analysis Complete!", state="complete")

            # Store in session
            st.session_state.current_result = result
            st.session_state.current_result_id = record_id
            st.session_state.current_transcript = video_info["transcript"]
            st.session_state.video_info = video_info
            
            # Cleanup
            video_path = video_info.get("video_path")
            if video_path:
                handler.cleanup(video_path)
            
            st.success("✅ Fact-check complete! Scroll down to see results.")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.exception(e)

    # Display Results
    if st.session_state.get("current_result"):
        res = st.session_state.current_result
        
        st.divider()
        st.header("📊 Fact-Check Results")
        
        # Overall metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            emoji = get_verdict_emoji(res.overall_rating)
            st.metric("Overall Rating", f"{emoji} {res.overall_rating}")
        
        with col2:
            st.metric("Confidence", f"{res.overall_confidence:.0%}")
        
        with col3:
            st.metric("Claims Found", res.claims_found)
        
        with col4:
            detected_lang = st.session_state.get('video_info', {}).get('detected_language', res.language)
            st.metric("Language", detected_lang.title())
        
        # Check for contradictions
        display_contradiction_warnings(res)
        
        # Summary
        st.info(f"**Summary:** {res.summary}")
        
        # Tabs
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📋 Detailed Analysis", 
            "📊 Visualizations",
            "📝 Transcript", 
            "💬 Ask Questions",
            "📄 Export Report",
            "📚 Learn More"
        ])
        
        with tab1:
            st.subheader("Claim-by-Claim Analysis")
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                filter_verdict = st.multiselect(
                    "Filter by verdict:",
                    options=["TRUE", "FALSE", "MIXED", "MOSTLY_TRUE", "MOSTLY_FALSE", "UNVERIFIED"],
                    default=[]
                )
            with col2:
                filter_category = st.multiselect(
                    "Filter by category:",
                    options=list(set([v.category for v in res.verdicts])),
                    default=[]
                )
            
            # Apply filters
            filtered_verdicts = res.verdicts
            if filter_verdict:
                filtered_verdicts = [v for v in filtered_verdicts if v.verdict in filter_verdict]
            if filter_category:
                filtered_verdicts = [v for v in filtered_verdicts if v.category in filter_category]
            
            if not filtered_verdicts:
                st.warning("No claims match your filters.")
            else:
                for i, v in enumerate(filtered_verdicts):
                    display_verdict_card(v, i)
        
        with tab2:
            st.subheader("Visual Analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                display_verdict_distribution(res.verdicts)
                display_category_breakdown(res.verdicts)
            
            with col2:
                display_confidence_chart(res.verdicts)
                display_evidence_quality_chart(res.verdicts)
        
        with tab3:
            st.subheader("Full Transcript")
            
            # Show corrections if any
            video_info = st.session_state.get('video_info', {})
            if video_info.get('corrections_applied'):
                st.success(f"✨ Transcript was automatically corrected using {video_info.get('correction_method', 'AI')}")
                
                with st.expander("View Original vs Corrected"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Original (Raw Whisper):**")
                        st.text_area("", value=video_info.get('original_transcript', ''), height=200, key="orig")
                    with col2:
                        st.markdown("**Corrected (AI Enhanced):**")
                        st.text_area("", value=st.session_state.current_transcript, height=200, key="corr")
            
            st.text_area(
                "Transcript", 
                value=st.session_state.current_transcript, 
                height=400,
                help="Full transcription of the video audio"
            )
            
            # Download transcript
            st.download_button(
                "💾 Download Transcript",
                data=st.session_state.current_transcript,
                file_name=f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        
        with tab4:
            st.subheader("Ask Questions About This Video")
            
            question = st.text_input(
                "Your question:",
                placeholder="e.g., Is acrylamide really dangerous? What are safer cooking alternatives?"
            )
            
            if question:
                with st.spinner("🤔 Thinking..."):
                    fc = get_fact_checker()
                    if fc:
                        try:
                            answer = fc.chat_about_video(question, res)
                            
                            st.markdown("### 💡 Answer:")
                            st.info(answer)
                            
                            # Save to database
                            record_id = st.session_state.current_result_id
                            db = get_database()
                            db.add_chat_message(record_id, "user", question)
                            db.add_chat_message(record_id, "assistant", answer)
                            
                        except Exception as e:
                            st.error(f"Error: {e}")
            
            # Show chat history
            if st.session_state.get('current_result_id'):
                db = get_database()
                chat_history = db.get_chat_history(st.session_state.current_result_id)
                
                if chat_history:
                    st.markdown("---")
                    st.subheader("Previous Questions")
                    
                    for msg in chat_history[-6:]:  # Show last 3 Q&A pairs
                        if msg['role'] == 'user':
                            st.markdown(f"**Q:** {msg['content']}")
                        else:
                            st.markdown(f"**A:** {msg['content']}")
                            st.markdown("---")
        
        with tab5:
            st.subheader("Export Fact-Check Report")
            
            report_gen = get_report_generator()
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📄 Generate PDF Report", use_container_width=True):
                    with st.spinner("Generating PDF..."):
                        try:
                            pdf_bytes = report_gen.generate_pdf(res, st.session_state.current_transcript)
                            
                            st.download_button(
                                "💾 Download PDF Report",
                                data=pdf_bytes,
                                file_name=f"health_factcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                            
                            st.success("✅ PDF generated successfully!")
                        except Exception as e:
                            st.error(f"Error generating PDF: {e}")
            
            with col2:
                if st.button("📊 Generate HTML Report", use_container_width=True):
                    with st.spinner("Generating HTML..."):
                        try:
                            html_content = report_gen.generate_html(res, st.session_state.current_transcript)
                            
                            st.download_button(
                                "💾 Download HTML Report",
                                data=html_content,
                                file_name=f"health_factcheck_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                                mime="text/html",
                                use_container_width=True
                            )
                            
                            st.success("✅ HTML generated successfully!")
                        except Exception as e:
                            st.error(f"Error generating HTML: {e}")
        
        with tab6:
            st.subheader("📚 Understanding the Results")
            
            st.markdown("""
            ### How This Works
            
            1. **Download & Transcribe**: We download the Instagram Reel and convert speech to text using Whisper AI
            2. **AI Correction**: Llama AI fixes any transcription errors (especially medical terms)
            3. **Claim Extraction**: Llama 3.3 identifies all health claims in the transcript
            4. **Multi-Source Verification**: We search 10+ medical databases:
               - PubMed (peer-reviewed research)
               - ClinicalTrials.gov
               - OpenAlex (250M+ papers)
               - Semantic Scholar
               - WHO, FDA, NIH databases
               - Built-in medical facts database
            5. **AI Analysis**: Llama evaluates evidence and assigns verdicts
            6. **Confidence Scoring**: Based on evidence quality and quantity
            
            ### Verdict Meanings
            
            - ✅ **TRUE**: Claim is well-supported by strong scientific evidence
            - ✅ **MOSTLY_TRUE**: Claim is generally accurate with minor caveats
            - ⚠️ **MIXED**: Claim has both supporting and contradicting evidence
            - ❌ **MOSTLY_FALSE**: Claim is largely inaccurate with some truth
            - ❌ **FALSE**: Claim contradicts scientific consensus
            - ❓ **UNVERIFIED**: Insufficient evidence to make a determination
            
            ### What To Do Next
            
            - **If claims are FALSE**: Be skeptical, don't follow advice
            - **If claims are MIXED**: Consult healthcare professionals
            - **If claims are TRUE**: Still consult professionals before making health decisions
            
            ⚠️ **Important**: This tool is for informational purposes only. Always consult qualified healthcare professionals for medical advice.
            """)
            
            st.markdown("""
            ### Report Issues or Suggest Improvements
            
            Found incorrect information? Have suggestions?  
            [Open an issue on GitHub](https://github.com/yourusername/health-factchecker)
            """)

if __name__ == "__main__":
    main()