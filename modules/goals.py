"""
Goals page — Add goals, view all active goals with progress bars.
"""

import datetime
import streamlit as st
import pandas as pd

from db.database import get_session
from db.models import Goal


def render():
    st.title("🎯 Goals")

    tabs = st.tabs(["Active Goals", "Add Goal", "All Goals"])

    # ------------------------------------------------------------------
    # Tab 1: Active Goals
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Active Goals")

        with get_session() as session:
            goals = (
                session.query(Goal)
                .filter(Goal.status == "active")
                .order_by(Goal.deadline)
                .all()
            )

        if not goals:
            st.info("No active goals. Add goals in the 'Add Goal' tab.")
        else:
            for goal in goals:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"### {goal.title}")
                        if goal.description:
                            st.caption(goal.description)

                        if goal.target_value and goal.target_value > 0:
                            current = goal.current_value or 0.0
                            progress_pct = min(1.0, max(0.0, current / goal.target_value))
                            st.progress(progress_pct)
                            st.caption(
                                f"{current} / {goal.target_value} {goal.unit or ''} "
                                f"({progress_pct * 100:.1f}%)"
                            )
                        else:
                            st.caption("No progress target set.")

                    with col2:
                        if goal.deadline:
                            days_left = (goal.deadline - datetime.date.today()).days
                            if days_left < 0:
                                st.error(f"⚠️ Overdue by {abs(days_left)} days")
                            elif days_left <= 7:
                                st.warning(f"⏳ {days_left} days left")
                            else:
                                st.info(f"📅 {days_left} days left")
                        else:
                            st.info("No deadline")

                    # Quick update current value
                    new_val = st.number_input(
                        f"Update current value for '{goal.title}'",
                        min_value=0.0,
                        value=float(goal.current_value or 0),
                        step=0.1,
                        key=f"update_goal_{goal.id}",
                    )
                    update_cols = st.columns(3)
                    with update_cols[0]:
                        if st.button("Update Progress", key=f"btn_update_{goal.id}"):
                            with get_session() as session:
                                g = session.query(Goal).filter(Goal.id == goal.id).first()
                                if g:
                                    g.current_value = new_val
                                    if g.target_value and new_val >= g.target_value:
                                        g.status = "completed"
                            st.success("Progress updated!")
                            st.rerun()
                    with update_cols[1]:
                        if st.button("Mark Complete", key=f"btn_complete_{goal.id}"):
                            with get_session() as session:
                                g = session.query(Goal).filter(Goal.id == goal.id).first()
                                if g:
                                    g.status = "completed"
                            st.success("Goal marked as complete!")
                            st.rerun()
                    with update_cols[2]:
                        if st.button("Pause", key=f"btn_pause_{goal.id}"):
                            with get_session() as session:
                                g = session.query(Goal).filter(Goal.id == goal.id).first()
                                if g:
                                    g.status = "paused"
                            st.info("Goal paused.")
                            st.rerun()

                    st.divider()

    # ------------------------------------------------------------------
    # Tab 2: Add Goal
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Add New Goal")

        with st.form("add_goal_form"):
            col1, col2 = st.columns(2)
            with col1:
                g_title = st.text_input("Goal Title", placeholder="Reach 180 lbs bodyweight")
                g_description = st.text_area("Description", placeholder="Describe your goal…")
                g_unit = st.text_input("Unit", placeholder="kg, lbs, reps, %…")
            with col2:
                g_target = st.number_input("Target Value", min_value=0.0, step=0.1)
                g_current = st.number_input("Current Value", min_value=0.0, step=0.1)
                g_deadline = st.date_input("Deadline", value=datetime.date.today() + datetime.timedelta(days=90))
                g_status = st.selectbox("Status", ["active", "paused"])

            g_submitted = st.form_submit_button("Add Goal")

        if g_submitted:
            if not g_title:
                st.error("Goal title is required.")
            else:
                with get_session() as session:
                    goal = Goal(
                        title=g_title,
                        description=g_description,
                        target_value=g_target or None,
                        current_value=g_current or None,
                        unit=g_unit,
                        deadline=g_deadline,
                        status=g_status,
                        created_at=datetime.date.today(),
                    )
                    session.add(goal)
                st.success(f"Goal '{g_title}' added!")
                st.rerun()

    # ------------------------------------------------------------------
    # Tab 3: All Goals
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("All Goals")

        status_filter = st.selectbox("Filter by Status", ["all", "active", "completed", "paused"])

        with get_session() as session:
            q = session.query(Goal)
            if status_filter != "all":
                q = q.filter(Goal.status == status_filter)
            goals = q.order_by(Goal.created_at.desc()).all()

        if not goals:
            st.info("No goals found.")
        else:
            rows = []
            for g in goals:
                if g.target_value and g.target_value > 0:
                    progress = f"{(g.current_value or 0) / g.target_value * 100:.1f}%"
                else:
                    progress = "N/A"
                rows.append({
                    "Title": g.title,
                    "Target": f"{g.target_value} {g.unit or ''}",
                    "Current": f"{g.current_value} {g.unit or ''}",
                    "Progress": progress,
                    "Deadline": str(g.deadline) if g.deadline else "—",
                    "Status": g.status,
                    "Created": str(g.created_at) if g.created_at else "—",
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
