import streamlit as st
import pandas as pd
import time
import os
import plotly.express as px
import plotly.graph_objects as go
from report import generate_pdf
from datetime import datetime
import random # Imported at top for cleaner code

# --- IMPORT BACKEND ---
try:
    from predictor import get_prediction, generate_clinical_summary, is_hindi_available, is_model_loaded
    from db import init_db, save_result, get_history
except ImportError as e:
    st.error(f"❌ CRITICAL ERROR: {e}")
    st.stop()

# --- 1. SETUP & CONFIG ---
st.set_page_config(
    page_title="NeuroSentinel | Cognitive Monitor",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "db_init" not in st.session_state:
    init_db()
    st.session_state["db_init"] = True

if not is_model_loaded():
    st.error(
        "⚠️ The classifier model failed to load on this server - every analysis will fail. "
        "This is a deployment/dependency problem, not something wrong with your audio. "
        "Check the app's deploy logs (Manage app > logs) for the Python traceback at startup."
    )

# --- DYNAMIC PATH SETUP (THE FIX) ---
# We calculate the path to brain.png relative to this file (app.py)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir) # Go up one level to root
logo_path = os.path.join(root_dir, "brain.png")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        /* Soft Dark Background */
        .stApp { background-color: #1A1F2B; color: #E0E6ED; }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] { background-color: #11141c; }

        /* Large, Accessible Metrics */
        div[data-testid="stMetricValue"] { font-size: 36px !important; color: #72CC96 !important; }
        div[data-testid="stMetricLabel"] { font-size: 18px !important; color: #bfbfbf !important; }

        /* Clinical Observations Box - Elder Friendly */
        .report-box {
            background-color: #242A38;
            color: #E0E6ED;
            padding: 24px;
            border-left: 8px solid #E58E8E;
            border-radius: 12px;
            font-size: 20px;
            line-height: 1.6;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* Large Touch Targets for Confirmation Buttons */
        .stButton>button {
            height: 60px;
            font-size: 20px !important;
            border-radius: 10px;
            font-weight: 500;
        }
        
        /* Metric container styling */
        div[data-testid="stMetric"] {
            background-color: #242A38;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR ---
with st.sidebar:
    # --- FIX APPLIED HERE ---
    if os.path.exists(logo_path):
        st.image(logo_path, width=80)
    else:
        st.write("🧠") # Fallback emoji so app doesn't crash
    # ------------------------
    
    st.title("NeuroSentinel")
    st.caption("v1.2 (Clinical Research Build)")
    st.markdown("---")
    
    st.header("👤 Patient Profile")
    
    # Generate unique patient ID on first load
    if "patient_id" not in st.session_state:
        st.session_state.patient_id = f"PT-{random.randint(1000, 9999)}-{random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'X', 'Y', 'Z'])}"
    
    patient_id = st.text_input("Patient ID / MRN", value=st.session_state.patient_id)
    st.info(f"Active Session: {patient_id}")
    st.markdown("---")

    st.subheader("🌐 Assessment Language")
    hindi_option = "Hindi (हिन्दी)" if is_hindi_available() else "Hindi (हिन्दी) — model not installed"
    language_display = st.selectbox("Recording Language", options=["English", hindi_option], index=0)
    language_code = "hi" if language_display.startswith("Hindi") else "en"
    if language_code == "hi":
        st.caption(
            "⚠️ Hindi analysis uses only the 4 waveform-derived biomarkers (acoustic "
            "texture, MFCC delta, brightness, pitch variance), scored by a separate "
            "model trained on the same English recordings - the 5 speech-to-text-derived "
            "biomarkers aren't used for Hindi since they can't be reliably corrected "
            "across languages with the data available. This is unvalidated on real Hindi "
            "speech in either direction (healthy or decline) - treat results as experimental."
        )
    st.markdown("---")

    if st.button("Reset Live Trial Stats"):
        st.session_state.session_correct = 0
        st.session_state.session_total = 0
        st.rerun()

# --- 3. MAIN APP LAYOUT ---
st.title("Cognitive Assessment Dashboard")
st.markdown(f"**Patient:** `{patient_id}` | **Date:** `{datetime.now().strftime('%Y-%m-%d')}`")

tab1, tab2, tab3 = st.tabs(["🎙️ New Assessment", "📊 Biomarker Details", "📈 Clinical History"])

# ==========================================
# TAB 1: LIVE RECORDING & ANALYSIS
# ==========================================
with tab1:
    # Custom CSS for Circular Recorder
    st.markdown("""
        <style>
            /* 1. The Main Container (The Red Circle) */
            div[data-testid="stAudioInput"] {
                width: 180px !important;
                height: 180px !important;
                margin: 0 auto;
                border-radius: 50% !important;
                background-color: #E63946 !important;
                box-shadow: 0 0 20px rgba(230, 57, 70, 0.6);
                border: 4px solid #fff;
                overflow: hidden; /* Clip inner content */
                display: flex;
                align-items: center;
                justify-content: center;
            }

            /* 2. Remove default backgrounds from ALL inner elements */
            div[data-testid="stAudioInput"] * {
                background-color: transparent !important;
            }

            /* 3. Style Text & Icons to be BLACK */
            div[data-testid="stAudioInput"] p, 
            div[data-testid="stAudioInput"] span,
            div[data-testid="stAudioInput"] div {
                color: #000000 !important;
                font-weight: 900 !important; /* Bold */
            }

            /* 4. Style Buttons (Microphone / Play) */
            div[data-testid="stAudioInput"] button {
                color: #000000 !important;
                border: none !important;
                transform: scale(1.5);
            }
            
            /* 5. Force Icons (SVG) to be black */
            div[data-testid="stAudioInput"] svg {
                fill: #000000 !important;
                color: #000000 !important;
            }

            /* 6. Make Waveform Black */
            div[data-testid="stAudioInput"] canvas {
                filter: brightness(0) !important;
                opacity: 0.8;
            }

            /* Hide the small "Record" label usually inside */
            div[data-testid="stAudioInput"] label {
                display: none !important;
            }

            .big-red-label {
                text-align: center;
                font-size: 20px;
                color: #E0E6ED;
                letter-spacing: 1px;
                margin-bottom: 25px;
                text-transform: uppercase;
                opacity: 0.8;
            }
        </style>
    """, unsafe_allow_html=True)

    # Centered Layout
    st.markdown("<div style='text-align: center; margin-top: 40px;'>", unsafe_allow_html=True)
    st.markdown("<p class='big-red-label'>Tap to Record</p>", unsafe_allow_html=True)

    if language_code == "hi":
        st.info(
            "🌐 Recording in Hindi: scoring uses only the 4 waveform-derived biomarkers "
            "(not the speech-to-text-derived ones). Unvalidated on real Hindi speech - "
            "treat as experimental."
        )

    # Audio Input
    audio_input = st.audio_input("Record")

    st.markdown("</div>", unsafe_allow_html=True)

    if audio_input:
        st.audio(audio_input, format="audio/wav")
        with open("temp_input.wav", "wb") as f:
            f.write(audio_input.getvalue())
        
        # Centered Analysis Button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("RUN ANALYSIS 🚀", type="primary", use_container_width=True):
                with st.spinner("Extracting 9 Neurological Biomarkers..."):
                    label, confidence, data, notes = get_prediction("temp_input.wav", language=language_code)

                    if data is not None:
                        # Pass entire data dict to save_result
                        save_result(patient_id, label, confidence, data, language=language_code)

                        report_path = generate_pdf(
                            patient_id,
                            {
                                "pause_rate": data['pause_rate'][0],
                                "vocab_richness": data['vocab_richness'][0],
                                "word_count": data['word_count'][0],
                                "speech_rate": data['speech_rate'][0],
                                "initial_latency": data['initial_latency'][0],
                                "acoustic_texture": data['acoustic_texture'][0],
                                "mfcc_delta": data['mfcc_delta'][0],
                                "speech_brightness": data['speech_brightness'][0],
                                "emotional_range": data['emotional_range'][0]
                            },
                            label
                        )

                        st.session_state['last_result'] = {
                            "label": label, "conf": confidence, "data": data,
                            "summary": generate_clinical_summary(data),
                            "report_path": report_path,
                            "language": language_code,
                            "notes": notes,
                        }
                        st.success("Analysis Complete! switch to 'Biomarker Details' tab to view results.")
                    elif label == "Model Error":
                        st.error(
                            "⚠️ The classifier model failed to load on this server (not an audio problem). "
                            "Check the app's deploy logs for the exact error - this usually means a "
                            "dependency version mismatch between training and deployment."
                        )
                    else:
                        st.error("Analysis Failed: Could not extract biomarkers. Please ensure you spoke clearly or try recording again.")

# ==========================================
# TAB 2: DETAILED BIOMARKERS
# ==========================================
with tab2:
    st.header("📊 Diagnostic Insights & Biomarker Analysis")
    
    if 'last_result' in st.session_state:
        res = st.session_state['last_result']
        data, label = res['data'], res['label']

        if res.get('language') == 'hi':
            st.info(
                "🌐 This result used only the 4 waveform-derived biomarkers below "
                "(the 5 speech-to-text-derived ones are shown for information but "
                "weren't part of the decision). Unvalidated on real Hindi speech - "
                "treat as experimental."
            )

        # --- Result Alert ---
        if label != "Healthy":
            st.error(f"🚨 RESULT: {label.upper()} (Confidence: {res['conf']*100:.0f}%)")
        else:
            st.success(f"✅ RESULT: {label.upper()} (Confidence: {res['conf']*100:.0f}%)")

        # --- Clinical Reasoning ---
        st.markdown(f"""<div class="report-box"><strong>Clinical Observations:</strong><br>{res['summary']}</div>""", unsafe_allow_html=True)

        # --- Recording Notes (quality tips, not a diagnostic claim) ---
        if res.get('notes'):
            st.markdown("##### 🎙️ Recording Notes")
            for note in res['notes']:
                st.info(note)

        st.markdown("##### 🧪 9-Point Neurological Panel")
        # Thresholds below are mean - 1 std (or + 1 std, direction depending on
        # the biomarker) of the real Healthy class in data/dataset.csv (157
        # real clinical recordings) - NOT the old thresholds eyeballed against
        # 7 short seed recordings. Recompute these if the training data changes.

        # Row 1
        m1, m2, m3 = st.columns(3)
        m1.metric("Pause Rate", f"{data['pause_rate'][0]:.2f}",
                    delta="Risk" if data['pause_rate'][0] > 0.35 else "Normal", delta_color="inverse")
        m2.metric("Vocab Richness", f"{data['vocab_richness'][0]:.2f}",
                    delta="Good" if data['vocab_richness'][0] > 0.55 else "Low", delta_color="normal" if data['vocab_richness'][0] > 0.55 else "inverse")
        m3.metric("Word Count", f"{data['word_count'][0]}",
                    delta="Good" if data['word_count'][0] > 80 else "Low", delta_color="normal" if data['word_count'][0] > 80 else "inverse")

        # Row 2
        m4, m5, m6 = st.columns(3)
        m4.metric("Speech Rate", f"{data['speech_rate'][0]:.1f} wps",
                    delta="Good" if data['speech_rate'][0] > 1.9 else "Slow", delta_color="normal" if data['speech_rate'][0] > 1.9 else "inverse")
        m5.metric("Initial Latency", f"{data['initial_latency'][0]:.2f}s",
                    delta="Fast" if data['initial_latency'][0] < 3.0 else "Delayed", delta_color="normal" if data['initial_latency'][0] < 3.0 else "inverse")
        m6.metric("Acoustic Texture", f"{data['acoustic_texture'][0]:.2f}",
                    delta="Clear" if data['acoustic_texture'][0] > -30 else "Muffled", delta_color="normal" if data['acoustic_texture'][0] > -30 else "inverse")

        # Row 3
        m7, m8, m9 = st.columns(3)
        m7.metric("MFCC Delta", f"{data['mfcc_delta'][0]:.4f}",
                    delta="Stable" if abs(data['mfcc_delta'][0]) < 0.015 else "Variable", delta_color="normal" if abs(data['mfcc_delta'][0]) < 0.015 else "inverse")
        m8.metric("Brightness", f"{data['speech_brightness'][0]:.0f} Hz",
                    delta="Good" if data['speech_brightness'][0] > 1600 else "Low", delta_color="normal" if data['speech_brightness'][0] > 1600 else "inverse")
        m9.metric("Emotional Range", f"{data['emotional_range'][0]:.1f}",
                    delta="Expressive" if data['emotional_range'][0] > 1000000 else "Flat", delta_color="normal" if data['emotional_range'][0] > 1000000 else "inverse")

        # --- Radar Chart ---
        st.markdown("##### 🧠 Neurological Fingerprint")
        categories = ['Pause Rate', 'Vocab', 'Texture', 'Brightness', 'Delta', 'Emotional Range', 'Speech Rate', 'Latency', 'Count']
        r_vals = [(1-data['pause_rate'][0])*100, data['vocab_richness'][0]*100, abs(data['acoustic_texture'][0]), 
                  (data['speech_brightness'][0]/4000)*100, abs(data['mfcc_delta'][0])*500, (data['emotional_range'][0]/5000)*100,
                  (data['speech_rate'][0]/3)*100, (1/max(1, data['initial_latency'][0]))*100, min(data['word_count'][0], 100)]

        fig = go.Figure()
        
        # 1. Healthy Baseline (Comparison)
        fig.add_trace(go.Scatterpolar(
            r=[85, 80, 70, 75, 80, 85, 80, 90, 80],
            theta=categories,
            fill='toself',
            name='Healthy Baseline',
            line_color='rgba(255, 255, 255, 0.3)',
            fillcolor='rgba(255, 255, 255, 0.05)',
            hoverinfo='skip'
        ))

        # 2. Patient Data
        # Dynamic Color Selection (Muted/Soft)
        fill_color = 'rgba(229, 142, 142, 0.5)' if label != "Healthy" else 'rgba(114, 204, 255, 0.5)'
        line_color = '#E58E8E' if label != "Healthy" else '#72CC96'
        
        fig.add_trace(go.Scatterpolar(
            r=r_vals, 
            theta=categories, 
            fill='toself', 
            name='Patient Scan', 
            line_color=line_color,
            fillcolor=fill_color,
            marker=dict(size=6, color=line_color)
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor='rgba(255,255,255,0.2)', gridcolor='rgba(255,255,255,0.1)'),
                angularaxis=dict(
                    tickfont=dict(size=12, color="#aaa", family="Arial"),
                    gridcolor='rgba(255,255,255,0.1)',
                    linecolor='rgba(255,255,255,0.2)'
                ),
                bgcolor='rgba(0,0,0,0)'
            ),
            height=400, 
            margin=dict(l=80, r=80, t=20, b=20),
            showlegend=True,
            legend=dict(font=dict(color="#ccc"), bgcolor="rgba(0,0,0,0)")
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Trial Accuracy (Separate Section)
        st.markdown("---")
        correct = st.session_state.get('session_correct', 0)
        total = st.session_state.get('session_total', 0)
        trial_acc = (correct / total * 100) if total > 0 else 0.0
        st.metric("Live Trial Accuracy", f"{trial_acc:.1f}%", delta=f"{total} Tests Performed")

        # --- ACTIONS & PDF ---
        st.markdown("---")
        st.caption("👨‍⚕️ Judge's Verdict: Confirm diagnosis to update live session stats.")
        v1, v2, v3 = st.columns([1, 1, 1.5])
        with v1:
            if st.button("✅ Confirm Correct"):
                st.session_state.session_correct = st.session_state.get('session_correct', 0) + 1
                st.session_state.session_total = st.session_state.get('session_total', 0) + 1
                st.rerun()
        with v2:
            if st.button("❌ Mark Incorrect"):
                st.session_state.session_total = st.session_state.get('session_total', 0) + 1
                st.rerun()
        with v3:
            if os.path.exists(res['report_path']):
                with open(res['report_path'], "rb") as f:
                    st.download_button("📄 Download PDF Report", f, 
                                     file_name=f"NeuroSentinel_{patient_id}.pdf")
        
    else:
        st.info("Run an analysis in the 'New Assessment' tab to see detailed metrics.")

# ==========================================
# TAB 3: HISTORY
# ==========================================
with tab3:
    st.subheader(f"History for {patient_id}")
    h_df = get_history(patient_id)
    if not h_df.empty:
        # Sort by ID (chronological)
        h_df = h_df.sort_values(by="id")
        
        # Mixed-language history is common once Hindi assessments exist for the
        # same patient; color by language so English/Hindi runs aren't silently
        # blended into one trend line.
        has_mixed_language = 'language' in h_df.columns and h_df['language'].nunique() > 1
        color_kwarg = {'color': 'language'} if has_mixed_language else {}

        # Graph 1: Pause Rate Trajectory
        fig_pause = px.line(h_df, x='timestamp', y='pause_rate', markers=True, title="Pause Rate Trajectory", **color_kwarg)
        fig_pause.add_hline(y=0.35, line_dash="dash", line_color="red", annotation_text="Risk Threshold (>0.35 = Risk)")
        if not has_mixed_language:
            fig_pause.update_traces(line_color='#E58E8E')
        st.plotly_chart(fig_pause, use_container_width=True)

        # Graph 2: Word Count Trajectory
        fig_words = px.line(h_df, x='timestamp', y='word_count', markers=True, title="Word Count Trajectory", **color_kwarg)
        fig_words.add_hline(y=80, line_dash="dash", line_color="white", annotation_text="Minimum Threshold (>80 = Good)")
        if not has_mixed_language:
            fig_words.update_traces(line_color='#72CC96')
        st.plotly_chart(fig_words, use_container_width=True)

        # Graph 3: Speech Rate Trajectory
        fig_rate = px.line(h_df, x='timestamp', y='speech_rate', markers=True, title="Speech Rate Trajectory", **color_kwarg)
        fig_rate.add_hline(y=1.9, line_dash="dash", line_color="orange", annotation_text="Minimum Threshold (>1.9 = Good)")
        if not has_mixed_language:
            fig_rate.update_traces(line_color='#72CCFF')
        st.plotly_chart(fig_rate, use_container_width=True)
        st.dataframe(h_df)
    else:
        st.warning("No historical records found.")

st.markdown("---")
st.caption("🔒 NeuroSentinel Edge AI | Research-grade screening aid, not a diagnostic tool")
