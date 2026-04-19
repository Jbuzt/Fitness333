"""
Gear page — Active Cycle, Injection Log, Insulin Log, Cycle Planner, Inventory.
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from db.database import get_session
from db.models import Compound, InjectionLog, InsulinLog, Meal
from components.charts import cycle_gantt_chart
from utils.notifications import get_active_compounds


INJECTION_SITES = [
    "left_glute", "right_glute",
    "left_quad", "right_quad",
    "left_delt", "right_delt",
    "other",
]

SITE_ROTATION = [
    "right_glute", "left_glute",
    "right_quad", "left_quad",
    "right_delt", "left_delt",
]


def _get_next_site(last_site: str) -> str:
    if last_site in SITE_ROTATION:
        idx = SITE_ROTATION.index(last_site)
        return SITE_ROTATION[(idx + 1) % len(SITE_ROTATION)]
    return SITE_ROTATION[0]


def render():
    st.title("💉 Gear")
    tabs = st.tabs(["Active Cycle", "Injection Log", "Insulin Log", "Cycle Planner", "Inventory"])

    # ------------------------------------------------------------------
    # Tab 1: Active Cycle
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Active Compounds")

        with get_session() as session:
            active = get_active_compounds(session)

        if not active:
            st.info("No active compounds. Add compounds in the Cycle Planner tab.")
        else:
            today = datetime.date.today()
            rows = []
            for c in active:
                if c.start_date:
                    week_num = (today - c.start_date).days // 7 + 1
                else:
                    week_num = "?"
                if c.end_date and c.start_date:
                    total_weeks = (c.end_date - c.start_date).days // 7 + 1
                else:
                    total_weeks = "?"
                rows.append({
                    "Compound": c.name,
                    "Type": c.type,
                    "Dose": f"{c.dose_mg} mg",
                    "Frequency": c.frequency,
                    "Route": c.administration,
                    "Cycle Week": f"Week {week_num} of {total_weeks}",
                    "Start": str(c.start_date) if c.start_date else "—",
                    "End": str(c.end_date) if c.end_date else "—",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # ------------------------------------------------------------------
    # Tab 2: Injection Log
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Injection Log")

        with get_session() as session:
            compounds = session.query(Compound).all()
            comp_names = [c.name for c in compounds]
            comp_map = {c.name: c.id for c in compounds}

            last_injection = (
                session.query(InjectionLog)
                .order_by(InjectionLog.date.desc(), InjectionLog.time.desc())
                .first()
            )

        last_site = last_injection.site if last_injection else SITE_ROTATION[-1]
        next_site = _get_next_site(last_site)
        st.info(f"💉 Last site: **{last_site.replace('_', ' ').title()}** → Next suggested: **{next_site.replace('_', ' ').title()}**")

        if not comp_names:
            st.warning("No compounds found. Add compounds in Cycle Planner.")
        else:
            with st.form("injection_log_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    inj_compound = st.selectbox("Compound", comp_names)
                    inj_date = st.date_input("Date", value=datetime.date.today())
                with col2:
                    inj_time = st.text_input("Time (HH:MM)", value=datetime.datetime.now().strftime("%H:%M"))
                    inj_dose = st.number_input("Dose (mg)", min_value=0.0, step=0.5)
                with col3:
                    inj_site = st.selectbox("Injection Site", INJECTION_SITES,
                                             index=INJECTION_SITES.index(next_site) if next_site in INJECTION_SITES else 0)
                    inj_notes = st.text_area("Notes")
                inj_submitted = st.form_submit_button("Log Injection")

            if inj_submitted:
                with get_session() as session:
                    log = InjectionLog(
                        compound_id=comp_map[inj_compound],
                        date=inj_date,
                        time=inj_time,
                        dose_mg=inj_dose,
                        site=inj_site,
                        notes=inj_notes,
                    )
                    session.add(log)
                st.success("Injection logged!")
                st.rerun()

        st.markdown("---")
        st.markdown("#### Injection History")
        filter_compound = st.selectbox("Filter by Compound", ["All"] + comp_names, key="inj_filter")

        with get_session() as session:
            q = session.query(InjectionLog).order_by(InjectionLog.date.desc())
            logs = q.all()
            all_compounds = {c.id: c.name for c in session.query(Compound).all()}

        if logs:
            rows = [{
                "Date": str(l.date),
                "Time": l.time or "—",
                "Compound": all_compounds.get(l.compound_id, "?"),
                "Dose (mg)": l.dose_mg,
                "Site": l.site.replace("_", " ").title() if l.site else "—",
                "Notes": l.notes or "",
            } for l in logs]
            df = pd.DataFrame(rows)
            if filter_compound != "All":
                df = df[df["Compound"] == filter_compound]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No injection logs yet.")

    # ------------------------------------------------------------------
    # Tab 3: Insulin Log
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Insulin Log")

        with st.form("insulin_log_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                ins_date = st.date_input("Date", value=datetime.date.today())
                ins_time = st.text_input("Time (HH:MM)", value=datetime.datetime.now().strftime("%H:%M"))
            with col2:
                ins_units = st.number_input("Units (IU)", min_value=0.0, step=0.5)
                ins_type = st.selectbox("Insulin Type", ["fast_acting", "slow_acting", "mixed"])
            with col3:
                ins_timing = st.selectbox(
                    "Timing relative to meal",
                    ["pre_meal", "post_meal", "fasted", "with_meal"],
                )
                ins_notes = st.text_area("Notes")
            ins_submitted = st.form_submit_button("Log Insulin")

        if ins_submitted:
            # Safety check: fasted insulin warning
            if ins_timing == "fasted":
                st.warning("⚠️ SAFETY FLAG: Insulin logged as fasted. This is potentially dangerous!")

            # Check if a meal was logged within 30 minutes
            with get_session() as session:
                today_meals = session.query(Meal).filter(Meal.date == ins_date).all()
                nearby_meal = False
                try:
                    inj_hour, inj_min = map(int, ins_time.split(":"))
                    inj_dt = datetime.datetime.combine(ins_date, datetime.time(inj_hour, inj_min))
                    for m in today_meals:
                        if m.time:
                            mh, mm = map(int, m.time.split(":"))
                            meal_dt = datetime.datetime.combine(ins_date, datetime.time(mh, mm))
                            if abs((inj_dt - meal_dt).total_seconds()) <= 1800:
                                nearby_meal = True
                                break
                except (ValueError, AttributeError):
                    pass

            if not nearby_meal and ins_timing != "fasted":
                st.warning("⚠️ No meal logged within 30 minutes. Consider logging a meal first.")

            with get_session() as session:
                log = InsulinLog(
                    date=ins_date,
                    time=ins_time,
                    units=ins_units,
                    insulin_type=ins_type,
                    timing_relative_to_meal=ins_timing,
                    notes=ins_notes,
                )
                session.add(log)
            st.success("Insulin dose logged!")
            st.rerun()

        st.markdown("---")
        st.markdown("#### Today's Insulin Total")
        with get_session() as session:
            today_insulin = session.query(InsulinLog).filter(InsulinLog.date == datetime.date.today()).all()
        total_iu = sum(l.units for l in today_insulin)
        st.metric("Total IU Today", f"{total_iu} IU")

        if today_insulin:
            rows = [{
                "Time": l.time or "—",
                "Units": l.units,
                "Type": l.insulin_type,
                "Timing": l.timing_relative_to_meal,
                "Notes": l.notes or "",
            } for l in today_insulin]
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # ------------------------------------------------------------------
    # Tab 4: Cycle Planner
    # ------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Cycle Planner")

        st.markdown("#### Add / Edit Compound")
        with st.form("add_compound_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                c_name = st.text_input("Compound Name", placeholder="Testosterone Enanthate")
                c_type = st.selectbox("Type", ["anabolic", "peptide", "sarm", "other"])
                c_ester = st.text_input("Ester", placeholder="Enanthate")
            with col2:
                c_dose = st.number_input("Dose (mg)", min_value=0.0, step=1.0)
                c_freq = st.selectbox("Frequency", ["daily", "eod", "e3d", "twice_weekly", "weekly"])
                c_admin = st.selectbox("Administration", ["injection", "oral", "topical"])
            with col3:
                c_start = st.date_input("Start Date", value=datetime.date.today())
                c_end = st.date_input("End Date", value=datetime.date.today() + datetime.timedelta(weeks=12))
                c_inv_ml = st.number_input("Inventory (ml)", min_value=0.0, step=1.0)
                c_conc = st.number_input("Concentration (mg/ml)", min_value=0.0, step=1.0)
            c_notes = st.text_area("Notes")
            c_submitted = st.form_submit_button("Add Compound")

        if c_submitted and c_name:
            with get_session() as session:
                compound = Compound(
                    name=c_name,
                    type=c_type,
                    ester=c_ester,
                    dose_mg=c_dose,
                    frequency=c_freq,
                    administration=c_admin,
                    start_date=c_start,
                    end_date=c_end,
                    inventory_ml=c_inv_ml,
                    concentration_mg_per_ml=c_conc,
                    notes=c_notes,
                )
                session.add(compound)
            st.success(f"Compound '{c_name}' added!")
            st.rerun()

        st.markdown("#### Compound Cycle Gantt Chart")
        with get_session() as session:
            compounds = session.query(Compound).all()

        if compounds:
            gantt_data = []
            for c in compounds:
                if c.start_date and c.end_date:
                    gantt_data.append({
                        "name": c.name,
                        "start_date": c.start_date,
                        "end_date": c.end_date,
                        "type": c.type,
                    })
            if gantt_data:
                fig = cycle_gantt_chart(gantt_data)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Add compounds with start/end dates to see the Gantt chart.")
        else:
            st.info("No compounds added yet.")

    # ------------------------------------------------------------------
    # Tab 5: Inventory
    # ------------------------------------------------------------------
    with tabs[4]:
        st.subheader("Compound Inventory")

        with get_session() as session:
            compounds = session.query(Compound).all()

        if not compounds:
            st.info("No compounds in inventory.")
        else:
            rows = []
            for c in compounds:
                if c.concentration_mg_per_ml and c.dose_mg and c.concentration_mg_per_ml > 0:
                    ml_per_dose = c.dose_mg / c.concentration_mg_per_ml
                    doses_left = c.inventory_ml / ml_per_dose if ml_per_dose > 0 else 0
                else:
                    doses_left = "N/A"
                rows.append({
                    "Compound": c.name,
                    "Inventory (ml)": c.inventory_ml,
                    "Conc. (mg/ml)": c.concentration_mg_per_ml,
                    "Dose (mg)": c.dose_mg,
                    "Doses Remaining": doses_left if isinstance(doses_left, str) else round(doses_left, 1),
                    "Notes": c.notes or "",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
