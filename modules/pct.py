"""
PCT Planner page — Active PCT, Protocol Builder, Recovery Tracker.
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.express as px

from db.database import get_session
from db.models import PCTProtocol, BloodWorkResult


def render():
    st.title("📋 PCT Planner")
    tabs = st.tabs(["Active PCT", "Protocol Builder", "Recovery Tracker"])

    # ------------------------------------------------------------------
    # Tab 1: Active PCT
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Active PCT Protocol")

        with get_session() as session:
            today = datetime.date.today()
            active_pct = (
                session.query(PCTProtocol)
                .filter(PCTProtocol.start_date <= today)
                .all()
            )
            active_pct = [
                p for p in active_pct
                if p.start_date and (
                    p.start_date + datetime.timedelta(weeks=p.duration_weeks or 0)
                ) >= today
            ]

        if not active_pct:
            st.info("No active PCT protocol. Build one in the Protocol Builder tab.")
        else:
            rows = []
            for p in active_pct:
                if p.start_date:
                    end = p.start_date + datetime.timedelta(weeks=p.duration_weeks or 0)
                    days_remaining = (end - today).days
                else:
                    days_remaining = "?"
                rows.append({
                    "Compound": p.compound_name,
                    "Dose (mg)": p.dose_mg,
                    "Frequency": p.frequency,
                    "Duration (weeks)": p.duration_weeks,
                    "Start Date": str(p.start_date) if p.start_date else "—",
                    "Days Remaining": days_remaining,
                    "Notes": p.notes or "",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

        # Countdown to PCT start (if any future PCT planned)
        with get_session() as session:
            future_pct = (
                session.query(PCTProtocol)
                .filter(PCTProtocol.start_date > today)
                .order_by(PCTProtocol.start_date)
                .first()
            )

        if future_pct:
            days_until = (future_pct.start_date - today).days
            st.info(f"⏳ Next PCT starts: **{future_pct.start_date}** ({days_until} days away)")

    # ------------------------------------------------------------------
    # Tab 2: Protocol Builder
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Build PCT Protocol")

        with st.form("add_pct_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                pct_compound = st.selectbox(
                    "Compound",
                    ["Nolvadex", "Clomid", "HCG", "Aromasin", "other"],
                )
                pct_dose = st.number_input("Dose (mg)", min_value=0.0, step=1.0)
            with col2:
                pct_freq = st.selectbox("Frequency", ["daily", "eod", "twice_weekly", "weekly"])
                pct_duration = st.number_input("Duration (weeks)", min_value=1, max_value=52, value=4)
            with col3:
                pct_start = st.date_input("Start Date", value=datetime.date.today())
                pct_cycle_end = st.date_input("Cycle End Date", value=datetime.date.today())
            pct_notes = st.text_area("Notes")
            pct_submitted = st.form_submit_button("Add to Protocol")

        if pct_submitted:
            with get_session() as session:
                pct = PCTProtocol(
                    cycle_end_date=pct_cycle_end,
                    compound_name=pct_compound,
                    dose_mg=pct_dose,
                    frequency=pct_freq,
                    duration_weeks=pct_duration,
                    start_date=pct_start,
                    notes=pct_notes,
                )
                session.add(pct)
            st.success(f"PCT compound '{pct_compound}' added!")
            st.rerun()

        st.markdown("---")
        st.markdown("#### All PCT Protocols")
        with get_session() as session:
            all_pct = session.query(PCTProtocol).order_by(PCTProtocol.start_date.desc()).all()

        if all_pct:
            rows = [{
                "Compound": p.compound_name,
                "Dose (mg)": p.dose_mg,
                "Frequency": p.frequency,
                "Duration (wk)": p.duration_weeks,
                "Start": str(p.start_date) if p.start_date else "—",
                "Cycle End": str(p.cycle_end_date) if p.cycle_end_date else "—",
            } for p in all_pct]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

            # Gantt of PCT timeline
            gantt_rows = []
            for p in all_pct:
                if p.start_date:
                    end = p.start_date + datetime.timedelta(weeks=p.duration_weeks or 4)
                    gantt_rows.append({
                        "Compound": p.compound_name,
                        "Start": p.start_date,
                        "Finish": end,
                    })
            if gantt_rows:
                df_gantt = pd.DataFrame(gantt_rows)
                fig = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Compound",
                                  title="PCT Timeline", color="Compound")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No PCT protocols defined yet.")

    # ------------------------------------------------------------------
    # Tab 3: Recovery Tracker
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Recovery Tracker — Natty Recovery Progress")

        st.markdown(
            "Track your natural hormone recovery after PCT by logging bloodwork markers "
            "(LH, FSH, Testosterone) in the Blood Work section."
        )

        with get_session() as session:
            recovery_markers = ["LH", "FSH", "Testosterone Total"]
            recovery_data = {}
            for marker in recovery_markers:
                results = (
                    session.query(BloodWorkResult)
                    .filter(BloodWorkResult.marker_name == marker)
                    .order_by(BloodWorkResult.date.desc())
                    .limit(1)
                    .first()
                )
                if results:
                    recovery_data[marker] = results

        # Reference baselines
        baselines = {
            "LH": (1.7, 8.6),
            "FSH": (1.5, 12.4),
            "Testosterone Total": (264, 916),
        }

        if not recovery_data:
            st.info("No recovery markers found. Log LH, FSH, and Testosterone in the Blood Work section.")
        else:
            for marker, result in recovery_data.items():
                low, high = baselines.get(marker, (0, 100))
                mid = (low + high) / 2
                pct_recovery = min(100.0, max(0.0, (result.value / mid) * 100.0))
                st.markdown(f"**{marker}:** {result.value} {result.unit or ''} (as of {result.date})")
                st.progress(int(pct_recovery))

            st.caption("Progress bars show approximate recovery toward mid-reference-range baseline.")
