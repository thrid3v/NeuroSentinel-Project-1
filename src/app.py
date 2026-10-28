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
    st.error(f"Critical error: {e}", icon=":material/error:")
    st.stop()

import ui

# --- 1. SETUP & CONFIG ---
st.set_page_config(
    page_title="NeuroSentinel | Cognitive Monitor",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "db_init" not in st.session_state:
    init_db()
    st.session_state["db_init"] = True

st.html(ui.CSS)

PROMPT_IMAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookiethief.png")

VIEWS = ["Assess", "Results", "History"]
if "nav" not in st.session_state:
    st.session_state.nav = "Assess"
if "_nav_target" in st.session_state:
    st.session_state.nav = st.session_state.pop("_nav_target")


def go_to(view):
    st.session_state.nav = view


# Generate unique patient ID on first load
if "patient_id" not in st.session_state:
    st.session_state.patient_id = f"PT-{random.randint(1000, 9999)}-{random.choice(['A', 'B', 'C', 'D', 'E', 'F', 'X', 'Y', 'Z'])}"

# --- 2. NAVBAR (brand / navigation / session menu) ---
with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="center", key="navbar"):
    st.html(ui.brand(), width="content")
    view = st.segmented_control("Navigation", VIEWS, required=True, key="nav", label_visibility="collapsed")

    session_label = st.session_state.get("patient_id_input", st.session_state.patient_id)
    with st.popover(session_label, icon=":material/badge:"):
        st.html(ui.card_title("Session", "Applies to new recordings and history."))
        patient_id = st.text_input("Patient ID / MRN", value=st.session_state.patient_id, key="patient_id_input")

        hindi_option = "Hindi (हिन्दी)" if is_hindi_available() else "Hindi (हिन्दी) — model not installed"
        language_display = st.selectbox("Recording language", options=["English", hindi_option], index=0)
        language_code = "hi" if language_display.startswith("Hindi") else "en"
        if language_code == "hi":
            st.caption(
                "Hindi analysis uses only the 4 waveform-derived biomarkers (acoustic "
                "texture, MFCC delta, brightness, pitch variance), scored by a separate "
                "model trained on the same English recordings - the 5 speech-to-text-derived "
                "biomarkers aren't used for Hindi since they can't be reliably corrected "
                "across languages with the data available. This is unvalidated on real Hindi "
                "speech in either direction (healthy or decline) - treat results as experimental."
            )

        if st.button("Reset live trial stats", icon=":material/refresh:", width="stretch"):
            st.session_state.session_correct = 0
            st.session_state.session_total = 0
            st.rerun()

# --- 3. PAGE ---
with st.container(key="page"):
    if not is_model_loaded():
        st.error(
            "The classifier model failed to load on this server - every analysis will fail. "
            "This is a deployment/dependency problem, not something wrong with your audio. "
            "Check the app's deploy logs (Manage app > logs) for the Python traceback at startup.",
            icon=":material/error:",
        )

    # ==========================================
    # ASSESS: LIVE RECORDING & ANALYSIS
    # ==========================================
    if view == "Assess":
        hero_text, hero_capture = st.columns([1.05, 1], gap="large", vertical_alignment="center")
        with hero_text:
            st.html(ui.hero(language_code, is_model_loaded()))

        with hero_capture:
            with st.container(key="capture", gap="medium"):
                st.html(ui.capture_header(patient_id))
                if os.path.exists(PROMPT_IMAGE):
                    st.image(PROMPT_IMAGE, width="stretch")
                    st.html('<p class="ns-prompt">Describe everything you see happening in this picture.</p>')
                else:
                    st.html(ui.SCOPE)

                if language_code == "hi":
                    st.info(
                        "Recording in Hindi: scoring uses only the 4 waveform-derived biomarkers "
                        "(not the speech-to-text-derived ones). Unvalidated on real Hindi speech - "
                        "treat as experimental.",
                        icon=":material/translate:",
                    )

                # Audio Input
                audio_input = st.audio_input("Record", label_visibility="collapsed")
                st.html(ui.hint("Tap the microphone to start, and again to stop. Aim for 30 to 60 seconds."))

                st.html(ui.divider("or upload a .wav file"))
                uploaded_file = st.file_uploader("Upload a WAV recording", type=["wav"], label_visibility="collapsed")

                # An uploaded file takes priority over a live recording when both are present.
                active_audio = uploaded_file if uploaded_file is not None else audio_input

                if active_audio:
                    st.audio(active_audio, format="audio/wav")
                    with open("temp_input.wav", "wb") as f:
                        f.write(active_audio.getvalue())

                    if st.button("Run analysis", icon=":material/graphic_eq:", type="primary", width="stretch"):
                        with st.spinner("Extracting 9 neurological biomarkers..."):
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
                                st.session_state["_nav_target"] = "Results"
                                st.rerun()
                            elif label == "Model Error":
                                st.error(
                                    "The classifier model failed to load on this server (not an audio problem). "
                                    "Check the app's deploy logs for the exact error - this usually means a "
                                    "dependency version mismatch between training and deployment.",
                                    icon=":material/error:",
                                )
                            else:
                                st.error(
                                    "Analysis failed: could not extract biomarkers. Please ensure you spoke "
                                    "clearly or try recording again.",
                                    icon=":material/error:",
                                )

        st.html(ui.MEASURES)

    # ==========================================
    # RESULTS: DETAILED BIOMARKERS
    # ==========================================
    elif view == "Results":
        if 'last_result' in st.session_state:
            res = st.session_state['last_result']
            data, label = res['data'], res['label']

            st.html(ui.page_header("Assessment results", patient_id, res.get('language')))

            if res.get('language') == 'hi':
                st.html(ui.callout(
                    "Experimental Hindi result",
                    "<p style='margin:0'>This result used only the 4 waveform-derived biomarkers below "
                    "(the 5 speech-to-text-derived ones are shown for information but weren't part of "
                    "the decision). Unvalidated on real Hindi speech - treat as experimental.</p>",
                    kind="info",
                ))

            result_col, actions_col = st.columns([1.7, 1], gap="medium")
            with result_col:
                st.html(ui.result_panel(label, res['conf'], res['summary']))
                # --- Recording Notes (quality tips, not a diagnostic claim) ---
                if res.get('notes'):
                    st.html(ui.notes_callout(res['notes']))

            with actions_col:
                with st.container(key="card-actions", gap="small"):
                    st.html(ui.card_title("Report", "Full biomarker breakdown with reference ranges."))
                    if os.path.exists(res['report_path']):
                        with open(res['report_path'], "rb") as f:
                            st.download_button("Download PDF report", f, icon=":material/download:",
                                               file_name=f"NeuroSentinel_{patient_id}.pdf", width="stretch")

                    st.space("small")
                    st.html(ui.card_title("Clinician feedback", "Confirm the result to update live session stats."))
                    correct = st.session_state.get('session_correct', 0)
                    total = st.session_state.get('session_total', 0)
                    trial_acc = (correct / total * 100) if total > 0 else 0.0
                    with st.container(horizontal=True, gap="small"):
                        if st.button("Confirm correct", icon=":material/check:", width="stretch"):
                            st.session_state.session_correct = st.session_state.get('session_correct', 0) + 1
                            st.session_state.session_total = st.session_state.get('session_total', 0) + 1
                            st.rerun()
                        if st.button("Mark incorrect", icon=":material/close:", width="stretch"):
                            st.session_state.session_total = st.session_state.get('session_total', 0) + 1
                            st.rerun()
                    st.html(ui.trial_stat(trial_acc, total))


            panel_col, chart_col = st.columns([1.45, 1], gap="medium")
            with panel_col:
                st.html(ui.biomarker_panel(data))

            with chart_col:
                with st.container(key="card-fingerprint"):
                    st.html(ui.card_title("Neurological fingerprint", "This scan against a healthy baseline, scaled 0 to 100."))
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
                        name='Healthy baseline',
                        line_color='rgba(232, 236, 242, 0.35)',
                        fillcolor='rgba(232, 236, 242, 0.05)',
                        hoverinfo='skip'
                    ))

                    # 2. Patient Data
                    fill_color = 'rgba(232, 103, 79, 0.4)' if label != "Healthy" else 'rgba(47, 213, 196, 0.35)'
                    line_color = '#E8674F' if label != "Healthy" else '#2FD5C4'

                    fig.add_trace(go.Scatterpolar(
                        r=r_vals,
                        theta=categories,
                        fill='toself',
                        name='This scan',
                        line_color=line_color,
                        fillcolor=fill_color,
                        marker=dict(size=5, color=line_color)
                    ))

                    fig.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Space Grotesk, sans-serif", color="#9BA5B4"),
                        polar=dict(
                            domain=dict(x=[0.14, 0.86]),
                            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor='rgba(232,236,242,0.12)', gridcolor='rgba(232,236,242,0.07)'),
                            angularaxis=dict(
                                tickfont=dict(size=11, color="#9BA5B4", family="Space Grotesk, sans-serif"),
                                gridcolor='rgba(232,236,242,0.07)',
                                linecolor='rgba(232,236,242,0.12)'
                            ),
                            bgcolor='rgba(0,0,0,0)'
                        ),
                        height=420,
                        margin=dict(l=84, r=84, t=24, b=24),
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5,
                                    font=dict(color="#9BA5B4"), bgcolor="rgba(0,0,0,0)")
                    )
                    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            st.html(ui.empty_state(
                "No results yet",
                "Record or upload a voice sample on the Assess page, then run the analysis. "
                "The result and full biomarker panel will appear here.",
            ))
            with st.container(horizontal_alignment="center"):
                st.button("Start an assessment", icon=":material/mic:", type="primary",
                          on_click=go_to, args=("Assess",))

    # ==========================================
    # HISTORY
    # ==========================================
    else:
        st.html(ui.page_header("Clinical history", patient_id))
        h_df = get_history(patient_id)
        if not h_df.empty:
            # Sort by ID (chronological)
            h_df = h_df.sort_values(by="id")

            # Mixed-language history is common once Hindi assessments exist for the
            # same patient; color by language so English/Hindi runs aren't silently
            # blended into one trend line.
            has_mixed_language = 'language' in h_df.columns and h_df['language'].nunique() > 1
            color_kwarg = {'color': 'language'} if has_mixed_language else {}

            st.html(ui.history_summary(h_df))

            trend_layout = dict(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Space Grotesk, sans-serif", color="#9BA5B4"),
                margin=dict(l=8, r=8, t=8, b=8),
                height=280,
                xaxis=dict(title=None, tickformat="%b %d\n%H:%M", nticks=4, tickangle=0),
                yaxis_title=None,
            )

            # Graph 1: Pause Rate Trajectory
            fig_pause = px.line(h_df, x='timestamp', y='pause_rate', markers=True, **color_kwarg)
            fig_pause.add_hline(y=0.35, line_dash="dash", line_color="#E8674F", annotation_text="Risk threshold 0.35")
            if not has_mixed_language:
                fig_pause.update_traces(line_color='#E8674F')
            fig_pause.update_layout(**trend_layout)

            # Graph 2: Word Count Trajectory
            fig_words = px.line(h_df, x='timestamp', y='word_count', markers=True, **color_kwarg)
            fig_words.add_hline(y=80, line_dash="dash", line_color="#E8ECF2", annotation_text="Minimum 80 words")
            if not has_mixed_language:
                fig_words.update_traces(line_color='#4ECB8D')
            fig_words.update_layout(**trend_layout)

            # Graph 3: Speech Rate Trajectory
            fig_rate = px.line(h_df, x='timestamp', y='speech_rate', markers=True, **color_kwarg)
            fig_rate.add_hline(y=1.9, line_dash="dash", line_color="#F2A65A", annotation_text="Minimum 1.9 wps")
            if not has_mixed_language:
                fig_rate.update_traces(line_color='#2FD5C4')
            fig_rate.update_layout(**trend_layout)

            trend_a, trend_b, trend_c = st.columns(3, gap="medium")
            for column, key, title, sub, fig_trend in [
                (trend_a, "card-trend-pause", "Pause rate", "Higher means more hesitation. Risk above 0.35.", fig_pause),
                (trend_b, "card-trend-words", "Word count", "Words per recording. Healthy above 80.", fig_words),
                (trend_c, "card-trend-rate", "Speech rate", "Words per second. Healthy above 1.9.", fig_rate),
            ]:
                with column:
                    with st.container(key=key):
                        st.html(ui.card_title(title, sub))
                        st.plotly_chart(fig_trend, width="stretch", config={"displayModeBar": False})

            with st.container(key="card-log"):
                st.html(ui.card_title("Session log", "Every assessment recorded for this patient."))
                st.dataframe(h_df, width="stretch", hide_index=True, column_config={
                    "id": "ID", "timestamp": "Recorded", "patient_id": "Patient", "risk_label": "Result",
                    "confidence": "Confidence", "pause_rate": "Pause rate", "vocab_richness": "Vocab richness",
                    "word_count": "Word count", "speech_rate": "Speech rate", "initial_latency": "Initial latency",
                    "acoustic_texture": "Acoustic texture", "mfcc_delta": "MFCC delta",
                    "speech_brightness": "Brightness", "emotional_range": "Emotional range", "language": "Language",
                })
        else:
            st.html(ui.empty_state(
                "No history for this patient",
                "Completed assessments are saved here automatically, so you can follow "
                "pause rate, word count and speech rate over time.",
            ))
            with st.container(horizontal_alignment="center"):
                st.button("Start an assessment", icon=":material/mic:", type="primary",
                          on_click=go_to, args=("Assess",), key="history_start")

st.html(ui.footer())
