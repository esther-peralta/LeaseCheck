"""LeaseCheck: Streamlit app. Run with:  streamlit run app.py"""

import os
from pathlib import Path

import streamlit as st

from checker import check_lease, extract_text

SAMPLES = Path(__file__).parent / "samples"
COLORS = {"red": "#d93025", "yellow": "#f2a600", "green": "#1e8e3e"}
LABELS = {"red": "High risk", "yellow": "Ask about this", "green": "Good to know"}

st.set_page_config(page_title="LeaseCheck", page_icon="🏠", layout="centered")

st.title("🏠 LeaseCheck")
st.write("Upload your lease and we'll flag clauses worth a second look **before you sign**.")
st.caption("LeaseCheck is not legal advice. It points out things to ask about and where to get free help.")

# ---------- API key (sidebar). Without one, the app runs in demo mode.
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input(
        "Anthropic API key (optional)",
        value=os.environ.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Leave blank to use demo mode (keyword matching, no AI).",
    )
    st.caption("No key = demo mode. Add a key to use AI.")

# ---------- Input: upload or sample
tab_upload, tab_sample = st.tabs(["Upload a lease", "Try a sample lease"])
lease_text = None

with tab_upload:
    uploaded = st.file_uploader("Lease file (.pdf or .txt)", type=["pdf", "txt"])
    if uploaded:
        lease_text = extract_text(uploaded.getvalue(), uploaded.name)
        if not lease_text.strip():
            st.error("Couldn't read any text. Scanned or photographed leases aren't supported yet.")
            lease_text = None

with tab_sample:
    samples = sorted(p.name for p in SAMPLES.glob("*.txt"))
    choice = st.selectbox("Sample lease", samples)
    if st.button("Use this sample"):
        st.session_state["sample_text"] = (SAMPLES / choice).read_text(encoding="utf-8")
    if "sample_text" in st.session_state and not uploaded:
        lease_text = st.session_state["sample_text"]
        with st.expander("View sample lease"):
            st.text(lease_text)

# ---------- Run the check
if lease_text and st.button("Check my lease", type="primary"):
    with st.spinner("Reading your lease..."):
        try:
            result = check_lease(lease_text, api_key=api_key or None)
        except Exception as e:  # show a friendly error instead of crashing during a demo
            st.error(f"Something went wrong: {e}")
            st.stop()

    findings = result["findings"]
    if result["mode"] == "demo":
        st.info("Demo mode: keyword matching only. Add an API key in the sidebar for AI review.")

    counts = {s: sum(f["severity"] == s for f in findings) for s in COLORS}
    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 High risk", counts["red"])
    c2.metric("🟡 Ask about this", counts["yellow"])
    c3.metric("🟢 Good to know", counts["green"])

    if not findings:
        st.success("No red flags found from our checklist. It's still worth getting a free review before you sign.")

    for f in findings:
        color = COLORS[f["severity"]]
        st.markdown(
            f"""<div style="border-left:6px solid {color};padding:0.6rem 1rem;margin:0.8rem 0;
            background:rgba(128,128,128,0.06);border-radius:4px">
            <div style="color:{color};font-weight:700;font-size:0.8rem">{LABELS[f['severity']].upper()}</div>
            <div style="font-weight:700;font-size:1.05rem">{f['name']}</div>
            <div style="font-style:italic;margin:0.4rem 0">“{f['quote']}”</div>
            <div>{f['explanation']}</div>
            <div style="margin-top:0.4rem"><b>Ask the landlord:</b> {f['question_to_ask']}</div>
            <div style="font-size:0.8rem;margin-top:0.4rem">Source: <a href="{f['source_url']}" target="_blank">{f['source_name']}</a></div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.divider()
    st.subheader("Get free help before you sign")
    st.markdown(
        "- **Temple Law students' Landlord-Tenant Help Service**: free lease reviews for Temple students "
        "([info](https://temple-university.helpscoutdocs.com/article/6642-landlord-tenant-help-service))\n"
        "- **Community Legal Services of Philadelphia** ([clsphila.org](https://clsphila.org/))"
    )
