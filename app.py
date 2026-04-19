"""
Fitness Tracker — Streamlit entry point.
Run with: streamlit run app.py
"""

import datetime
import streamlit as st

from db.database import init_db, get_session
from utils.notifications import (
    get_low_stock_supplements,
    get_active_compounds,
    get_todays_meals,
    get_todays_workout,
)
from utils.macros import daily_macro_summary

# Page configuration must be the very first Streamlit call
st.set_page_config(
    page_title="Fitness Tracker",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialise database (idempotent)
init_db()

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
PAGES = {
    "🏠 Dashboard": "dashboard",
    "💊 Supplementation": "supplementation",
    "🥗 Diet": "diet",
    "🏋️ Workout": "workout",
    "💉 Gear": "gear",
    "📏 Body Metrics": "body_metrics",
    "🩸 Blood Work": "blood_work",
    "📋 PCT Planner": "pct",
    "😴 Wellbeing": "wellbeing",
    "🎯 Goals": "goals",
}

with st.sidebar:
    st.title("🏋️ Fitness Tracker")
    st.markdown("---")

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "dashboard"

    for label, page_key in PAGES.items():
        if st.button(label, key=f"nav_{page_key}", use_container_width=True):
            st.session_state["current_page"] = page_key

    st.markdown("---")
    st.caption(f"Today: {datetime.date.today().strftime('%A, %d %b %Y')}")


# ---------------------------------------------------------------------------
# Dashboard (Home)
# ---------------------------------------------------------------------------
def render_dashboard():
    st.title("🏠 Dashboard — Today's Summary")

    today = datetime.date.today()

    with get_session() as session:
        low_stock = get_low_stock_supplements(session)
        active_compounds = get_active_compounds(session)
        todays_meals = get_todays_meals(session)
        todays_workout = get_todays_workout(session)
        todays_macros = daily_macro_summary(session, today)

    calorie_target = st.session_state.get("tdee_target", 2500.0)

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        calories_eaten = todays_macros.get("calories", 0.0)
        delta = calories_eaten - calorie_target
        st.metric(
            "Calories Today",
            f"{calories_eaten:.0f} kcal",
            delta=f"{delta:+.0f} kcal",
            delta_color="normal",
        )
    with col2:
        st.metric("Meals Logged", len(todays_meals))
    with col3:
        st.metric("Workout Today", "✅ Yes" if todays_workout else "❌ No")
    with col4:
        st.metric("Active Compounds", len(active_compounds))

    st.divider()

    # Active compounds
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 💉 Active Compounds")
        if active_compounds:
            for c in active_compounds:
                if c.start_date:
                    week_num = (today - c.start_date).days // 7 + 1
                    st.markdown(f"- **{c.name}** — {c.dose_mg} mg ({c.frequency}) · Week **{week_num}**")
                else:
                    st.markdown(f"- **{c.name}** — {c.dose_mg} mg ({c.frequency})")
        else:
            st.info("No active compounds.")

    with col_b:
        st.markdown("#### 🍽 Today's Meals")
        if todays_meals:
            for meal in todays_meals:
                st.markdown(f"- **{meal.meal_name.title()}** at {meal.time or '?'}")
        else:
            st.info("No meals logged today.")

    st.divider()

    # Macro summary
    st.markdown("#### 🥦 Today's Macro Summary")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Protein", f"{todays_macros.get('protein', 0):.1f}g")
    m_col2.metric("Carbs", f"{todays_macros.get('carbs', 0):.1f}g")
    m_col3.metric("Fat", f"{todays_macros.get('fat', 0):.1f}g")
    m_col4.metric("Fiber", f"{todays_macros.get('fiber', 0):.1f}g")

    # Low stock alerts
    if low_stock:
        st.divider()
        st.markdown("#### ⚠️ Low Stock Alerts")
        for item in low_stock:
            st.warning(
                f"**{item['name']}** — {item['quantity']} {item['unit']} remaining "
                f"(~{item['days_remaining']} days at current dose)"
            )


# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------
current_page = st.session_state.get("current_page", "dashboard")

if current_page == "dashboard":
    render_dashboard()

elif current_page == "supplementation":
    from modules.supplementation import render
    render()

elif current_page == "diet":
    from modules.diet import render
    render()

elif current_page == "workout":
    from modules.workout import render
    render()

elif current_page == "gear":
    from modules.gear import render
    render()

elif current_page == "body_metrics":
    from modules.body_metrics import render
    render()

elif current_page == "blood_work":
    from modules.blood_work import render
    render()

elif current_page == "pct":
    from modules.pct import render
    render()

elif current_page == "wellbeing":
    from modules.wellbeing import render
    render()

elif current_page == "goals":
    from modules.goals import render
    render()
