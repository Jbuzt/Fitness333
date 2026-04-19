"""
Supplementation page — Inventory, Log Usage, Schedule, Analytics.
"""

import datetime
import streamlit as st
import pandas as pd

from db.database import get_session
from db.models import Supplement, SupplementLog
from components.charts import calorie_bar_chart


def render():
    st.title("💊 Supplementation")
    tabs = st.tabs(["Inventory", "Log Usage", "Schedule", "Analytics"])

    # ------------------------------------------------------------------
    # Tab 1: Inventory
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Supplement Inventory")

        with get_session() as session:
            supplements = session.query(Supplement).all()
            if supplements:
                rows = []
                for s in supplements:
                    if s.daily_dose and s.daily_dose > 0:
                        days_rem = round(s.quantity / s.daily_dose, 1)
                    else:
                        days_rem = "N/A"

                    rows.append({
                        "Name": s.name,
                        "Stock": f"{s.quantity} {s.unit}",
                        "Daily Dose": f"{s.daily_dose} {s.dose_unit}",
                        "Days Remaining": days_rem,
                        "Timing": s.dose_timing,
                        "Expiry": str(s.expiry_date) if s.expiry_date else "—",
                        "Notes": s.notes or "",
                    })
                df = pd.DataFrame(rows)

                def highlight_low(row):
                    try:
                        days = float(row["Days Remaining"])
                        if days < 7:
                            return ["background-color: #ffcccc"] * len(row)
                    except (ValueError, TypeError):
                        pass
                    return [""] * len(row)

                st.dataframe(df.style.apply(highlight_low, axis=1), use_container_width=True)
            else:
                st.info("No supplements in inventory yet. Add one below.")

        st.markdown("---")
        st.subheader("Add New Supplement")
        with st.form("add_supplement_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input("Name", placeholder="Whey Protein")
                quantity = st.number_input("Quantity", min_value=0.0, step=0.1)
                unit = st.selectbox("Unit", ["g", "kg", "caps", "ml", "tabs"])
            with col2:
                daily_dose = st.number_input("Daily Dose", min_value=0.0, step=0.1)
                dose_unit = st.selectbox("Dose Unit", ["g", "kg", "caps", "ml", "tabs"])
                dose_timing = st.selectbox(
                    "Timing", ["morning", "pre-workout", "post-workout", "night", "other"]
                )
            with col3:
                cost_per_unit = st.number_input("Cost per Unit ($)", min_value=0.0, step=0.01)
                purchase_date = st.date_input("Purchase Date", value=datetime.date.today())
                expiry_date = st.date_input("Expiry Date", value=None)
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Add Supplement")

        if submitted:
            if not name:
                st.error("Supplement name is required.")
            else:
                with get_session() as session:
                    sup = Supplement(
                        name=name,
                        quantity=quantity,
                        unit=unit,
                        purchase_date=purchase_date,
                        expiry_date=expiry_date if expiry_date else None,
                        daily_dose=daily_dose,
                        dose_unit=dose_unit,
                        dose_timing=dose_timing,
                        cost_per_unit=cost_per_unit,
                        notes=notes,
                    )
                    session.add(sup)
                st.success(f"Supplement '{name}' added!")
                st.rerun()

    # ------------------------------------------------------------------
    # Tab 2: Log Usage
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Log Supplement Usage")

        with get_session() as session:
            supplements = session.query(Supplement).all()
            sup_names = [s.name for s in supplements]
            sup_map = {s.name: s.id for s in supplements}

        if not sup_names:
            st.info("Add supplements to inventory first.")
        else:
            with st.form("log_usage_form"):
                col1, col2 = st.columns(2)
                with col1:
                    sup_name = st.selectbox("Supplement", sup_names)
                    amount_used = st.number_input("Amount Used", min_value=0.0, step=0.1)
                with col2:
                    log_date = st.date_input("Date", value=datetime.date.today())
                    log_notes = st.text_area("Notes")
                log_submitted = st.form_submit_button("Log Usage")

            if log_submitted:
                with get_session() as session:
                    sup = session.query(Supplement).filter(Supplement.id == sup_map[sup_name]).first()
                    if sup:
                        log = SupplementLog(
                            supplement_id=sup.id,
                            date=log_date,
                            amount_used=amount_used,
                            notes=log_notes,
                        )
                        sup.quantity = max(0.0, sup.quantity - amount_used)
                        session.add(log)
                st.success("Usage logged and stock updated!")
                st.rerun()

        st.markdown("---")
        st.subheader("Recent Usage Logs")
        with get_session() as session:
            logs = (
                session.query(SupplementLog)
                .order_by(SupplementLog.date.desc())
                .limit(30)
                .all()
            )
            if logs:
                log_data = []
                for log in logs:
                    sup = session.query(Supplement).filter(Supplement.id == log.supplement_id).first()
                    log_data.append({
                        "Date": str(log.date),
                        "Supplement": sup.name if sup else "Unknown",
                        "Amount": log.amount_used,
                        "Notes": log.notes or "",
                    })
                st.dataframe(pd.DataFrame(log_data), use_container_width=True)
            else:
                st.info("No usage logs yet.")

    # ------------------------------------------------------------------
    # Tab 3: Schedule
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Supplement Timing Schedule")

        with get_session() as session:
            supplements = session.query(Supplement).all()

        timings = ["morning", "pre-workout", "post-workout", "night", "other"]
        schedule = {t: [] for t in timings}

        for s in supplements:
            timing = s.dose_timing if s.dose_timing in timings else "other"
            schedule[timing].append(f"{s.name} ({s.daily_dose} {s.dose_unit})")

        schedule_df = pd.DataFrame(
            {t.replace("-", " ").title(): ["\n".join(v) if v else "—"] for t, v in schedule.items()}
        )
        st.table(schedule_df.T.rename(columns={0: "Supplements"}))

    # ------------------------------------------------------------------
    # Tab 4: Analytics
    # ------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Supplement Analytics")

        with get_session() as session:
            logs = session.query(SupplementLog).all()
            supplements = session.query(Supplement).all()

        if not logs:
            st.info("No usage data yet.")
            return

        sup_map_id = {s.id: s.name for s in supplements}

        log_df = pd.DataFrame([{
            "date": log.date,
            "supplement": sup_map_id.get(log.supplement_id, "Unknown"),
            "amount": log.amount_used,
        } for log in logs])
        log_df["date"] = pd.to_datetime(log_df["date"])
        log_df["month"] = log_df["date"].dt.to_period("M").astype(str)

        monthly = log_df.groupby(["month", "supplement"])["amount"].sum().reset_index()

        import plotly.express as px
        fig = px.bar(monthly, x="month", y="amount", color="supplement",
                     title="Monthly Usage per Supplement", barmode="group")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Cost Summary")
        st.caption(
            "ℹ️ Monthly cost = daily_dose × 30 × cost_per_unit. "
            "Ensure daily_dose and cost_per_unit use the same unit (e.g. both in grams, or both per capsule)."
        )
        cost_data = []
        for s in supplements:
            if s.daily_dose and s.daily_dose > 0 and s.cost_per_unit > 0:
                monthly_cost = s.daily_dose * 30 * s.cost_per_unit
                cost_data.append({"Supplement": s.name, "Monthly Cost ($)": round(monthly_cost, 2)})
        if cost_data:
            st.dataframe(pd.DataFrame(cost_data), use_container_width=True)
