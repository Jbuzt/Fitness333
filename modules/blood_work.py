"""
Blood Work Tracker page — Log Results, Markers Dashboard, Trends.
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from db.database import get_session
from db.models import BloodWorkResult
from components.charts import bloodwork_status_table


COMMON_MARKERS = [
    ("Testosterone Total", "ng/dL", 264, 916),
    ("Testosterone Free", "pg/mL", 8.7, 25.1),
    ("Estradiol (E2)", "pg/mL", 7.6, 42.6),
    ("LH", "mIU/mL", 1.7, 8.6),
    ("FSH", "mIU/mL", 1.5, 12.4),
    ("Hematocrit", "%", 38.3, 48.6),
    ("Hemoglobin", "g/dL", 13.2, 17.1),
    ("ALT (SGPT)", "U/L", 7, 56),
    ("AST (SGOT)", "U/L", 10, 40),
    ("Creatinine", "mg/dL", 0.74, 1.35),
    ("HDL Cholesterol", "mg/dL", 40, 60),
    ("LDL Cholesterol", "mg/dL", 0, 100),
    ("Total Cholesterol", "mg/dL", 0, 200),
    ("PSA", "ng/mL", 0, 4),
    ("RBC", "M/uL", 4.32, 5.72),
    ("WBC", "K/uL", 3.5, 10.5),
]


def render():
    st.title("🩸 Blood Work")
    tabs = st.tabs(["Log Results", "Markers Dashboard", "Trends"])

    # ------------------------------------------------------------------
    # Tab 1: Log Results
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Log Bloodwork Results")

        with st.form("log_bloodwork_form"):
            col1, col2 = st.columns(2)
            with col1:
                bw_date = st.date_input("Collection Date", value=datetime.date.today())
                marker_options = [m[0] for m in COMMON_MARKERS] + ["Custom"]
                marker_choice = st.selectbox("Marker", marker_options)
                if marker_choice == "Custom":
                    marker_name = st.text_input("Custom Marker Name")
                    ref_min = st.number_input("Reference Min", step=0.01)
                    ref_max = st.number_input("Reference Max", step=0.01)
                    marker_unit = st.text_input("Unit")
                else:
                    marker_name = marker_choice
                    defaults = {m[0]: m for m in COMMON_MARKERS}
                    _, marker_unit, ref_min, ref_max = defaults[marker_choice]
            with col2:
                bw_value = st.number_input("Value", step=0.01)
                bw_notes = st.text_area("Notes")

            bw_submitted = st.form_submit_button("Log Result")

        if bw_submitted:
            if not marker_name:
                st.error("Marker name is required.")
            else:
                with get_session() as session:
                    result = BloodWorkResult(
                        date=bw_date,
                        marker_name=marker_name,
                        value=bw_value,
                        unit=marker_unit,
                        reference_min=ref_min,
                        reference_max=ref_max,
                        notes=bw_notes,
                    )
                    session.add(result)
                st.success(f"Bloodwork result for '{marker_name}' logged!")
                st.rerun()

    # ------------------------------------------------------------------
    # Tab 2: Markers Dashboard
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Markers Dashboard")

        with get_session() as session:
            results = session.query(BloodWorkResult).order_by(BloodWorkResult.date.desc()).all()

        if not results:
            st.info("No bloodwork data logged yet.")
        else:
            # Get latest result per marker
            latest = {}
            for r in results:
                if r.marker_name not in latest:
                    latest[r.marker_name] = r

            rows = []
            for marker, r in latest.items():
                status = "Normal"
                if r.reference_min is not None and r.reference_max is not None:
                    v = r.value
                    low, high = r.reference_min, r.reference_max
                    margin = (high - low) * 0.1
                    if v < low - margin or v > high + margin:
                        status = "Out of Range"
                    elif v < low or v > high:
                        status = "Borderline"

                rows.append({
                    "Marker": r.marker_name,
                    "Value": r.value,
                    "Unit": r.unit or "",
                    "Ref Min": r.reference_min,
                    "Ref Max": r.reference_max,
                    "Date": str(r.date),
                    "Status": status,
                })

            df = pd.DataFrame(rows)

            def color_status(val):
                if val == "Normal":
                    return "background-color: #c8e6c9"
                elif val == "Borderline":
                    return "background-color: #fff9c4"
                elif val == "Out of Range":
                    return "background-color: #ffcdd2"
                return ""

            st.dataframe(
                df.style.applymap(color_status, subset=["Status"]),
                use_container_width=True,
            )

    # ------------------------------------------------------------------
    # Tab 3: Trends
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Marker Trends")

        with get_session() as session:
            results = session.query(BloodWorkResult).order_by(BloodWorkResult.date).all()

        if not results:
            st.info("No bloodwork data yet.")
            return

        all_markers = sorted(set(r.marker_name for r in results))
        sel_marker = st.selectbox("Select Marker", all_markers)

        marker_results = [r for r in results if r.marker_name == sel_marker]

        if marker_results:
            df = pd.DataFrame([{
                "date": r.date,
                "value": r.value,
                "ref_min": r.reference_min,
                "ref_max": r.reference_max,
            } for r in marker_results])
            df["date"] = pd.to_datetime(df["date"])

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["date"], y=df["value"],
                                     mode="lines+markers", name=sel_marker,
                                     line=dict(color="steelblue")))

            ref_min = df["ref_min"].iloc[-1]
            ref_max = df["ref_max"].iloc[-1]
            if ref_min is not None and ref_max is not None:
                fig.add_hrect(y0=ref_min, y1=ref_max,
                              fillcolor="green", opacity=0.1,
                              annotation_text="Reference Range", annotation_position="top right")
                fig.add_hline(y=ref_min, line_dash="dot", line_color="green")
                fig.add_hline(y=ref_max, line_dash="dot", line_color="green")

            fig.update_layout(title=f"{sel_marker} Over Time",
                              xaxis_title="Date", yaxis_title=f"Value ({marker_results[0].unit or ''})")
            st.plotly_chart(fig, use_container_width=True)
