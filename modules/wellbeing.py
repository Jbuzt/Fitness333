"""
Wellbeing & Recovery Log page — Daily Log, Trends, Side Effect Journal.
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.express as px

from db.database import get_session
from db.models import WellbeingLog
from components.charts import wellbeing_trends_chart


def render():
    st.title("😴 Wellbeing & Recovery")
    tabs = st.tabs(["Daily Log", "Trends", "Side Effect Journal"])

    # ------------------------------------------------------------------
    # Tab 1: Daily Log
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Log Today's Wellbeing")

        with st.form("wellbeing_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                wb_date = st.date_input("Date", value=datetime.date.today())
                mood = st.slider("Mood Score (1–10)", 1, 10, 7)
                energy = st.slider("Energy Score (1–10)", 1, 10, 7)
            with col2:
                sleep_hours = st.number_input("Sleep Hours", min_value=0.0, max_value=24.0,
                                               step=0.5, value=8.0)
                sleep_quality = st.slider("Sleep Quality (1–10)", 1, 10, 7)
                libido = st.slider("Libido Score (1–10)", 1, 10, 7)
            with col3:
                side_effects = st.text_area("Side Effects (if any)", placeholder="Acne, water retention…")
                wb_notes = st.text_area("Notes")
            wb_submitted = st.form_submit_button("Save Log")

        if wb_submitted:
            with get_session() as session:
                log = WellbeingLog(
                    date=wb_date,
                    mood_score=mood,
                    energy_score=energy,
                    sleep_hours=sleep_hours,
                    sleep_quality=sleep_quality,
                    libido_score=libido,
                    side_effects=side_effects,
                    notes=wb_notes,
                )
                session.add(log)
            st.success("Wellbeing log saved!")
            st.rerun()

        st.markdown("---")
        st.subheader("Today's Log")
        with get_session() as session:
            today_log = (
                session.query(WellbeingLog)
                .filter(WellbeingLog.date == datetime.date.today())
                .first()
            )
        if today_log:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Mood", f"{today_log.mood_score}/10")
            col2.metric("Energy", f"{today_log.energy_score}/10")
            col3.metric("Sleep", f"{today_log.sleep_hours}h (Q:{today_log.sleep_quality}/10)")
            col4.metric("Libido", f"{today_log.libido_score}/10")
            if today_log.side_effects:
                st.warning(f"Side Effects: {today_log.side_effects}")
        else:
            st.info("No wellbeing log for today yet.")

    # ------------------------------------------------------------------
    # Tab 2: Trends
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Wellbeing Trends")

        with get_session() as session:
            logs = session.query(WellbeingLog).order_by(WellbeingLog.date).all()

        if not logs:
            st.info("No wellbeing data yet.")
            return

        df = pd.DataFrame([{
            "date": l.date,
            "mood_score": l.mood_score,
            "energy_score": l.energy_score,
            "sleep_quality": l.sleep_quality,
            "libido_score": l.libido_score,
            "sleep_hours": l.sleep_hours,
        } for l in logs])

        fig = wellbeing_trends_chart(df)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Sleep Hours")
        fig2 = px.bar(df, x="date", y="sleep_hours", title="Sleep Hours Over Time",
                      color_discrete_sequence=["purple"])
        st.plotly_chart(fig2, use_container_width=True)

    # ------------------------------------------------------------------
    # Tab 3: Side Effect Journal
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Side Effect Journal")

        with get_session() as session:
            logs = session.query(WellbeingLog).order_by(WellbeingLog.date.desc()).all()

        se_logs = [l for l in logs if l.side_effects and l.side_effects.strip()]

        if not se_logs:
            st.info("No side effects logged.")
            return

        df = pd.DataFrame([{
            "Date": str(l.date),
            "Side Effects": l.side_effects,
            "Mood": l.mood_score,
            "Energy": l.energy_score,
            "Notes": l.notes or "",
        } for l in se_logs])

        col1, col2 = st.columns(2)
        with col1:
            search = st.text_input("Search side effects", placeholder="acne, bloat…")
        with col2:
            date_range = st.date_input("Date Range", value=[
                datetime.date.today() - datetime.timedelta(days=90),
                datetime.date.today(),
            ])

        filtered = df.copy()
        if search:
            filtered = filtered[filtered["Side Effects"].str.contains(search, case=False, na=False)]
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            start_d, end_d = date_range
            filtered = filtered[
                (pd.to_datetime(filtered["Date"]).dt.date >= start_d) &
                (pd.to_datetime(filtered["Date"]).dt.date <= end_d)
            ]

        st.dataframe(filtered, use_container_width=True)
