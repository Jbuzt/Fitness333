"""
Body Metrics page — Log Metrics, Progress Charts, Measurements.
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from db.database import get_session
from db.models import BodyMetric
from components.charts import weight_trend_chart


def render():
    st.title("📏 Body Metrics")
    tabs = st.tabs(["Log Metrics", "Progress Charts", "Measurements"])

    # ------------------------------------------------------------------
    # Tab 1: Log Metrics
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Log Today's Metrics")

        with st.form("log_metrics_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                m_date = st.date_input("Date", value=datetime.date.today())
                weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
                body_fat = st.number_input("Body Fat (%)", min_value=0.0, max_value=100.0, step=0.1)
                muscle_mass = st.number_input("Muscle Mass (kg)", min_value=0.0, step=0.1)
            with col2:
                waist = st.number_input("Waist (cm)", min_value=0.0, step=0.1)
                chest = st.number_input("Chest (cm)", min_value=0.0, step=0.1)
                neck = st.number_input("Neck (cm)", min_value=0.0, step=0.1)
            with col3:
                left_arm = st.number_input("Left Arm (cm)", min_value=0.0, step=0.1)
                right_arm = st.number_input("Right Arm (cm)", min_value=0.0, step=0.1)
                left_leg = st.number_input("Left Leg (cm)", min_value=0.0, step=0.1)
                right_leg = st.number_input("Right Leg (cm)", min_value=0.0, step=0.1)
            m_notes = st.text_area("Notes")
            m_submitted = st.form_submit_button("Save Metrics")

        if m_submitted:
            with get_session() as session:
                metric = BodyMetric(
                    date=m_date,
                    weight_kg=weight or None,
                    body_fat_percent=body_fat or None,
                    muscle_mass_kg=muscle_mass or None,
                    waist_cm=waist or None,
                    chest_cm=chest or None,
                    neck_cm=neck or None,
                    left_arm_cm=left_arm or None,
                    right_arm_cm=right_arm or None,
                    left_leg_cm=left_leg or None,
                    right_leg_cm=right_leg or None,
                    notes=m_notes,
                )
                session.add(metric)
            st.success("Metrics saved!")
            st.rerun()

        st.markdown("---")
        st.subheader("Recent Metrics")
        with get_session() as session:
            metrics = session.query(BodyMetric).order_by(BodyMetric.date.desc()).limit(10).all()
        if metrics:
            rows = [{
                "Date": str(m.date),
                "Weight (kg)": m.weight_kg,
                "Body Fat (%)": m.body_fat_percent,
                "Muscle (kg)": m.muscle_mass_kg,
                "Waist (cm)": m.waist_cm,
            } for m in metrics]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No metrics logged yet.")

    # ------------------------------------------------------------------
    # Tab 2: Progress Charts
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Progress Charts")

        with get_session() as session:
            metrics = session.query(BodyMetric).order_by(BodyMetric.date).all()

        if not metrics:
            st.info("No body metrics logged yet.")
            return

        df = pd.DataFrame([{
            "date": m.date,
            "weight_kg": m.weight_kg,
            "body_fat_percent": m.body_fat_percent,
            "muscle_mass_kg": m.muscle_mass_kg,
        } for m in metrics])
        df["date"] = pd.to_datetime(df["date"])

        st.markdown("#### Weight Trend")
        if df["weight_kg"].notna().any():
            weight_df = df.dropna(subset=["weight_kg"])
            fig = weight_trend_chart(weight_df)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Body Fat % Over Time")
        if df["body_fat_percent"].notna().any():
            bf_df = df.dropna(subset=["body_fat_percent"])
            fig2 = px.line(bf_df, x="date", y="body_fat_percent",
                           title="Body Fat % Over Time", markers=True)
            fig2.update_traces(line_color="orange")
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("#### Muscle Mass Over Time")
        if df["muscle_mass_kg"].notna().any():
            mm_df = df.dropna(subset=["muscle_mass_kg"])
            fig3 = px.line(mm_df, x="date", y="muscle_mass_kg",
                           title="Muscle Mass Over Time", markers=True)
            fig3.update_traces(line_color="green")
            st.plotly_chart(fig3, use_container_width=True)

    # ------------------------------------------------------------------
    # Tab 3: Measurements (Radar Chart)
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Body Measurements — Radar Chart")

        with get_session() as session:
            metrics = session.query(BodyMetric).order_by(BodyMetric.date.desc()).limit(2).all()

        if not metrics:
            st.info("No measurements logged yet.")
            return

        measurement_keys = ["waist_cm", "chest_cm", "left_arm_cm", "right_arm_cm",
                            "left_leg_cm", "right_leg_cm", "neck_cm"]
        labels = ["Waist", "Chest", "Left Arm", "Right Arm", "Left Leg", "Right Leg", "Neck"]

        fig = go.Figure()
        colors = ["blue", "orange"]
        for i, m in enumerate(metrics):
            values = [getattr(m, k) or 0 for k in measurement_keys]
            values_closed = values + [values[0]]
            labels_closed = labels + [labels[0]]
            fig.add_trace(go.Scatterpolar(
                r=values_closed,
                theta=labels_closed,
                fill="toself",
                name=str(m.date),
                line_color=colors[i % len(colors)],
            ))

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            title="Body Measurements Radar Chart",
        )
        st.plotly_chart(fig, use_container_width=True)

        all_metrics = []
        with get_session() as session:
            all_m = session.query(BodyMetric).order_by(BodyMetric.date.desc()).all()
        for m in all_m:
            row = {"Date": str(m.date)}
            for key, label in zip(measurement_keys, labels):
                row[label] = getattr(m, key)
            all_metrics.append(row)

        if all_metrics:
            st.dataframe(pd.DataFrame(all_metrics), use_container_width=True)
