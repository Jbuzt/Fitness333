"""
Workout page — Log Workout, Routine Builder, Progress, Volume Tracker.
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from db.database import get_session
from db.models import WorkoutSession, Exercise, ExerciseSet
from components.charts import muscle_volume_chart


def _seed_exercises(session):
    """Add default exercises if none exist."""
    if session.query(Exercise).count() == 0:
        defaults = [
            ("Bench Press", "chest", "barbell"),
            ("Squat", "legs", "barbell"),
            ("Deadlift", "back", "barbell"),
            ("Overhead Press", "shoulders", "barbell"),
            ("Barbell Row", "back", "barbell"),
            ("Pull-up", "back", "bodyweight"),
            ("Dip", "chest", "bodyweight"),
            ("Bicep Curl", "arms", "dumbbell"),
            ("Tricep Pushdown", "arms", "cable"),
            ("Leg Press", "legs", "machine"),
            ("Lateral Raise", "shoulders", "dumbbell"),
            ("Plank", "core", "bodyweight"),
        ]
        for name, mg, eq in defaults:
            session.add(Exercise(name=name, muscle_group=mg, equipment=eq))
        session.commit()


def render():
    st.title("🏋️ Workout")
    tabs = st.tabs(["Log Workout", "Routine Builder", "Progress", "Volume Tracker"])

    with get_session() as session:
        _seed_exercises(session)

    # ------------------------------------------------------------------
    # Tab 1: Log Workout
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Log a Workout Session")

        with get_session() as session:
            exercises = session.query(Exercise).order_by(Exercise.name).all()
            ex_names = [e.name for e in exercises]
            ex_map = {e.name: e.id for e in exercises}
            ex_mg = {e.name: e.muscle_group for e in exercises}

        with st.form("log_workout_form"):
            col1, col2 = st.columns(2)
            with col1:
                wo_date = st.date_input("Date", value=datetime.date.today())
                wo_phase = st.selectbox("Phase", ["bulk", "cut", "maintenance", "recomp"])
                wo_duration = st.number_input("Duration (min)", min_value=1, value=60)
            with col2:
                wo_rpe = st.slider("Overall RPE", 1.0, 10.0, 7.0, step=0.5)
                wo_notes = st.text_area("Notes")

            st.markdown("#### Exercise Sets")
            num_sets = st.number_input("How many set entries?", min_value=1, max_value=30, value=4)
            set_data = []
            for i in range(int(num_sets)):
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    sel_ex = st.selectbox(f"Exercise #{i+1}", ex_names, key=f"ex_{i}")
                with c2:
                    reps = st.number_input("Reps", min_value=1, max_value=100, value=10, key=f"reps_{i}")
                with c3:
                    weight = st.number_input("Weight (kg)", min_value=0.0, step=0.5, key=f"wt_{i}")
                with c4:
                    rpe_set = st.slider("RPE", 1.0, 10.0, 7.0, step=0.5, key=f"rpe_{i}")
                with c5:
                    rest = st.number_input("Rest (s)", min_value=0, value=90, key=f"rest_{i}")
                set_data.append({"exercise": sel_ex, "reps": reps, "weight": weight, "rpe": rpe_set, "rest": rest})

            wo_submitted = st.form_submit_button("Save Workout")

        if wo_submitted:
            with get_session() as session:
                wo = WorkoutSession(
                    date=wo_date,
                    phase=wo_phase,
                    notes=wo_notes,
                    duration_minutes=wo_duration,
                    overall_rpe=wo_rpe,
                )
                session.add(wo)
                session.flush()
                for i, sd in enumerate(set_data):
                    ex_id = ex_map.get(sd["exercise"])
                    if ex_id:
                        es = ExerciseSet(
                            workout_session_id=wo.id,
                            exercise_id=ex_id,
                            set_number=i + 1,
                            reps=sd["reps"],
                            weight_kg=sd["weight"],
                            rpe=sd["rpe"],
                            rest_seconds=sd["rest"],
                        )
                        session.add(es)
            st.success("Workout saved!")
            st.rerun()

        st.markdown("---")
        st.markdown("#### Add Custom Exercise")
        with st.form("add_exercise_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                ex_name = st.text_input("Exercise Name")
            with col2:
                ex_mg_sel = st.selectbox(
                    "Muscle Group",
                    ["chest", "back", "legs", "shoulders", "arms", "core", "full_body"],
                )
            with col3:
                ex_eq = st.text_input("Equipment", placeholder="barbell, dumbbell, cable…")
            ex_submitted = st.form_submit_button("Add Exercise")

        if ex_submitted and ex_name:
            with get_session() as session:
                existing = session.query(Exercise).filter(Exercise.name == ex_name).first()
                if existing:
                    st.warning("Exercise already exists.")
                else:
                    session.add(Exercise(name=ex_name, muscle_group=ex_mg_sel, equipment=ex_eq))
            st.success(f"Exercise '{ex_name}' added!")
            st.rerun()

    # ------------------------------------------------------------------
    # Tab 2: Routine Builder
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Weekly Routine Builder")
        st.info("Plan your week by assigning muscle groups to each day.")

        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        muscle_groups = ["Rest", "chest", "back", "legs", "shoulders", "arms", "core", "full_body"]

        if "routine" not in st.session_state:
            st.session_state["routine"] = {d: "Rest" for d in days}

        with st.form("routine_form"):
            for day in days:
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.markdown(f"**{day}**")
                with col2:
                    st.session_state["routine"][day] = st.selectbox(
                        day, muscle_groups,
                        index=muscle_groups.index(st.session_state["routine"].get(day, "Rest")),
                        key=f"routine_{day}",
                        label_visibility="collapsed",
                    )
            st.form_submit_button("Save Routine")

        st.markdown("#### Current Routine")
        routine_df = pd.DataFrame([
            {"Day": d, "Focus": mg}
            for d, mg in st.session_state["routine"].items()
        ])
        st.dataframe(routine_df, use_container_width=True)

    # ------------------------------------------------------------------
    # Tab 3: Progress
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Exercise Progress & PRs")

        with get_session() as session:
            exercises = session.query(Exercise).order_by(Exercise.name).all()
            ex_names = [e.name for e in exercises]

        if not ex_names:
            st.info("No exercises found.")
            return

        sel_ex = st.selectbox("Select Exercise", ex_names, key="progress_ex")

        with get_session() as session:
            ex_obj = session.query(Exercise).filter(Exercise.name == sel_ex).first()
            if ex_obj:
                sets = (
                    session.query(ExerciseSet, WorkoutSession)
                    .join(WorkoutSession, ExerciseSet.workout_session_id == WorkoutSession.id)
                    .filter(ExerciseSet.exercise_id == ex_obj.id)
                    .order_by(WorkoutSession.date)
                    .all()
                )
                if sets:
                    rows = [{"date": ws.date, "weight_kg": es.weight_kg, "reps": es.reps} for es, ws in sets]
                    df = pd.DataFrame(rows)
                    df["date"] = pd.to_datetime(df["date"])
                    df["1RM_estimate"] = df["weight_kg"] * (1 + df["reps"] / 30)

                    fig = px.line(df, x="date", y="weight_kg", title=f"{sel_ex} — Weight Over Time",
                                  markers=True)
                    st.plotly_chart(fig, use_container_width=True)

                    pr_row = df.loc[df["weight_kg"].idxmax()]
                    st.success(f"🏆 PR: **{pr_row['weight_kg']} kg** on {str(pr_row['date'])[:10]}")

                    fig2 = px.line(df, x="date", y="1RM_estimate",
                                   title=f"{sel_ex} — Estimated 1RM Over Time", markers=True)
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info(f"No sets logged for {sel_ex} yet.")

    # ------------------------------------------------------------------
    # Tab 4: Volume Tracker
    # ------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Weekly Volume Tracker")

        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        week_end = week_start + datetime.timedelta(days=6)

        col1, col2 = st.columns(2)
        with col1:
            vs = st.date_input("Week Start", value=week_start, key="vol_start")
        with col2:
            ve = st.date_input("Week End", value=week_end, key="vol_end")

        with get_session() as session:
            sessions_in_range = (
                session.query(WorkoutSession)
                .filter(WorkoutSession.date >= vs, WorkoutSession.date <= ve)
                .all()
            )
            volume = {}
            for wo in sessions_in_range:
                for es in wo.sets:
                    mg = es.exercise.muscle_group if es.exercise else "unknown"
                    volume[mg] = volume.get(mg, 0) + 1

        if volume:
            vol_df = pd.DataFrame([{"muscle_group": mg, "sets": s} for mg, s in volume.items()])
            fig = muscle_volume_chart(vol_df)
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("**Recommended Weekly Sets per Muscle Group:**")
            rec_df = pd.DataFrame([
                {"Muscle Group": mg, "Min Sets": lo, "Max Sets": hi}
                for mg, (lo, hi) in {
                    "chest": (10, 20), "back": (10, 20), "legs": (12, 20),
                    "shoulders": (8, 16), "arms": (6, 14), "core": (6, 14)
                }.items()
            ])
            st.dataframe(rec_df, use_container_width=True)
        else:
            st.info("No workouts logged for this week.")
