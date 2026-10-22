import streamlit as st

import eah_core as core

REFRESH_RATE = core.REFRESH_RATE
# Share one reading between every open browser: a reading is reused until it
# is almost one refresh interval old, so N viewers still cost one poll.
CACHE_TTL = max(1, REFRESH_RATE - 1)

st.set_page_config(
    page_title="Einstein@Home Monitor", page_icon="⚛️", layout="wide"
)

st.markdown(
    """
    <style>
    @media (max-width: 640px) {
        div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def cached_gpu():
    return core.get_gpu_stats()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def cached_boinc():
    return core.get_boinc_tasks()


# --- UI Layout ---
st.title("⚛️ Einstein@Home & GPU Monitor")


# Wrap dashboard in a fragment to auto-refresh every N seconds without full page reloads
@st.fragment(run_every=REFRESH_RATE)
def render_dashboard():
    # 1. GPU Section
    st.subheader("📟 GPU Metrics")
    gpu_result = cached_gpu()
    gpu = gpu_result["gpu"]

    if gpu:
        g1, g2, g3 = st.columns(3)
        g1.metric("GPU Temperature", f"{gpu['temp']} °C" if gpu["temp"] is not None else "N/A")
        g2.metric("GPU Load", f"{gpu['util']} %" if gpu["util"] is not None else "N/A")
        g3.metric(
            "VRAM Usage",
            f"{gpu['mem_pct']} %" if gpu["mem_pct"] is not None else "N/A",
        )
        if gpu["mem_used"] is not None and gpu["mem_total"] is not None:
            g3.caption(f"{gpu['mem_used']} / {gpu['mem_total']} MB")
    else:
        st.error(f"GPU stats unavailable: {gpu_result['error']}")

    st.divider()

    # 2. BOINC / Einstein@Home Tasks Section
    st.subheader("🌌 Active Einstein@Home Tasks")
    boinc = cached_boinc()

    if boinc["error"]:
        st.error(f"Cannot read BOINC: {boinc['error']}")
    elif boinc["tasks"]:
        for task in boinc["tasks"]:
            with st.container():
                st.markdown(f"**Task:** `{task['name']}`")
                col_p, col_s, col_t = st.columns([3, 1, 1])

                with col_p:
                    st.progress(
                        task["progress"] / 100,
                        text=f"Progress: {task['progress']}%",
                    )
                with col_s:
                    st.caption(f"**Status:** {task['status']}")
                with col_t:
                    st.caption(f"**{task['time_label']}:** {task['elapsed_min']} min")
    else:
        st.info("No active Einstein@Home tasks currently running.")

    st.caption(
        f"Updated {max(gpu_result['fetched'], boinc['fetched'])} "
        f"(readings are shared and refreshed at most every {CACHE_TTL} s)"
    )
    if boinc["raw"]:
        with st.expander("Raw boinccmd output (for troubleshooting)"):
            st.code(boinc["raw"])


# Run the fragment
render_dashboard()
