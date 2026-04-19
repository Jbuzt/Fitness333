"""
Diet page — Food Log, Meal Timeline, Pantry, Macros & Targets, Digestion.
"""

import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from db.database import get_session
from db.models import Food, FoodInventory, Meal, MealEntry
from utils.macros import calculate_meal_macros, calculate_tdee, daily_macro_summary, weekly_calorie_average
from utils.digestion import estimate_digestion
from components.charts import macro_pie_chart, calorie_bar_chart


def render():
    st.title("🥗 Diet")
    tabs = st.tabs(["Food Log", "Meal Timeline", "Pantry", "Macros & Targets", "Digestion"])

    # ------------------------------------------------------------------
    # Tab 1: Food Log
    # ------------------------------------------------------------------
    with tabs[0]:
        st.subheader("Food Log")

        with get_session() as session:
            foods = session.query(Food).all()
            food_names = [f.name for f in foods]
            food_map = {f.name: f for f in foods}

        # Add a meal entry
        st.markdown("#### Log a Meal")
        with st.form("add_meal_form"):
            col1, col2 = st.columns(2)
            with col1:
                meal_date = st.date_input("Date", value=datetime.date.today())
                meal_time = st.text_input("Time (HH:MM)", value=datetime.datetime.now().strftime("%H:%M"))
                meal_name = st.selectbox(
                    "Meal Name",
                    ["breakfast", "lunch", "dinner", "snack", "pre-workout", "post-workout"],
                )
            with col2:
                if food_names:
                    selected_foods = st.multiselect("Foods", food_names)
                else:
                    st.warning("No foods in database. Add foods in the Pantry tab.")
                    selected_foods = []
            amounts = {}
            for fn in selected_foods:
                amounts[fn] = st.number_input(f"{fn} (grams)", min_value=0.0, step=10.0, key=f"amt_{fn}")
            meal_notes = st.text_area("Notes")
            meal_submitted = st.form_submit_button("Log Meal")

        if meal_submitted and selected_foods:
            with get_session() as session:
                meal = Meal(date=meal_date, time=meal_time, meal_name=meal_name, notes=meal_notes)
                session.add(meal)
                session.flush()
                for fn in selected_foods:
                    food = session.query(Food).filter(Food.name == fn).first()
                    if food:
                        entry = MealEntry(meal_id=meal.id, food_id=food.id, amount_grams=amounts.get(fn, 100.0))
                        session.add(entry)
            st.success("Meal logged!")
            st.rerun()

        st.markdown("---")
        st.markdown("#### Today's Meals")
        with get_session() as session:
            today = datetime.date.today()
            meals = session.query(Meal).filter(Meal.date == today).all()
            if meals:
                for meal in meals:
                    macros = calculate_meal_macros(meal.entries)
                    with st.expander(f"🍽 {meal.meal_name.title()} — {meal.time or '?'} ({macros['calories']} kcal)"):
                        rows = []
                        for entry in meal.entries:
                            if entry.food:
                                ratio = entry.amount_grams / 100.0
                                rows.append({
                                    "Food": entry.food.name,
                                    "Amount (g)": entry.amount_grams,
                                    "Calories": round(entry.food.calories_per_100g * ratio, 1),
                                    "Protein (g)": round(entry.food.protein_per_100g * ratio, 1),
                                    "Carbs (g)": round(entry.food.carbs_per_100g * ratio, 1),
                                    "Fat (g)": round(entry.food.fat_per_100g * ratio, 1),
                                })
                        if rows:
                            st.dataframe(pd.DataFrame(rows), use_container_width=True)
                        st.markdown(
                            f"**Total:** {macros['calories']} kcal | "
                            f"P: {macros['protein']}g | C: {macros['carbs']}g | F: {macros['fat']}g"
                        )
            else:
                st.info("No meals logged today.")

    # ------------------------------------------------------------------
    # Tab 2: Meal Timeline
    # ------------------------------------------------------------------
    with tabs[1]:
        st.subheader("Meal Timeline")

        timeline_date = st.date_input("Date", value=datetime.date.today(), key="timeline_date")

        with get_session() as session:
            meals = session.query(Meal).filter(Meal.date == timeline_date).all()

        if not meals:
            st.info("No meals logged for this date.")
        else:
            timeline_rows = []
            for meal in meals:
                macros = calculate_meal_macros(meal.entries)
                try:
                    hour, minute = map(int, meal.time.split(":")) if meal.time else (12, 0)
                    start = datetime.datetime.combine(timeline_date, datetime.time(hour, minute))
                    end = start + datetime.timedelta(minutes=30)
                except (ValueError, AttributeError):
                    start = datetime.datetime.combine(timeline_date, datetime.time(12, 0))
                    end = start + datetime.timedelta(minutes=30)

                timeline_rows.append({
                    "Meal": meal.meal_name.title(),
                    "Start": start,
                    "Finish": end,
                    "Calories": macros["calories"],
                })

            df_tl = pd.DataFrame(timeline_rows)
            fig = px.timeline(df_tl, x_start="Start", x_end="Finish", y="Meal",
                               color="Calories", title="Meal Timeline")
            fig.update_layout(xaxis_title="Time of Day")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### Calories by Meal")
            cal_df = pd.DataFrame({"Meal": [r["Meal"] for r in timeline_rows],
                                   "Calories": [r["Calories"] for r in timeline_rows]})
            fig2 = px.bar(cal_df, x="Meal", y="Calories", title="Calories per Meal")
            st.plotly_chart(fig2, use_container_width=True)

    # ------------------------------------------------------------------
    # Tab 3: Pantry
    # ------------------------------------------------------------------
    with tabs[2]:
        st.subheader("Pantry — Food Inventory")

        with get_session() as session:
            foods = session.query(Food).all()

        st.markdown("#### Food Database")
        if foods:
            food_df = pd.DataFrame([{
                "Name": f.name,
                "Type": f.food_type,
                "Calories/100g": f.calories_per_100g,
                "Protein/100g": f.protein_per_100g,
                "Carbs/100g": f.carbs_per_100g,
                "Fat/100g": f.fat_per_100g,
            } for f in foods])
            st.dataframe(food_df, use_container_width=True)
        else:
            st.info("No foods yet. Add some below.")

        st.markdown("#### Add Food to Database")
        with st.form("add_food_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                food_name = st.text_input("Food Name")
                food_type = st.selectbox(
                    "Food Type",
                    ["simple_carb", "complex_carb", "protein", "fat", "vegetable", "fruit", "dairy"],
                )
            with col2:
                cal100 = st.number_input("Calories/100g", min_value=0.0, step=1.0)
                prot100 = st.number_input("Protein/100g", min_value=0.0, step=0.1)
                carbs100 = st.number_input("Carbs/100g", min_value=0.0, step=0.1)
            with col3:
                fat100 = st.number_input("Fat/100g", min_value=0.0, step=0.1)
                fiber100 = st.number_input("Fiber/100g", min_value=0.0, step=0.1)
                sugar100 = st.number_input("Sugar/100g", min_value=0.0, step=0.1)
            food_submitted = st.form_submit_button("Add Food")

        if food_submitted and food_name:
            with get_session() as session:
                existing = session.query(Food).filter(Food.name == food_name).first()
                if existing:
                    st.warning(f"'{food_name}' already exists.")
                else:
                    from utils.digestion import FOOD_SPECIFIC_OVERRIDES, DIGESTION_TIMES
                    dig_time = FOOD_SPECIFIC_OVERRIDES.get(food_name.lower(), DIGESTION_TIMES.get(food_type, 120))
                    food = Food(
                        name=food_name,
                        food_type=food_type,
                        calories_per_100g=cal100,
                        protein_per_100g=prot100,
                        carbs_per_100g=carbs100,
                        fat_per_100g=fat100,
                        fiber_per_100g=fiber100,
                        sugar_per_100g=sugar100,
                        digestion_time_minutes=dig_time,
                    )
                    session.add(food)
                st.success(f"Food '{food_name}' added!")
                st.rerun()

        st.markdown("#### Pantry Stock")
        with get_session() as session:
            inventory = session.query(FoodInventory).all()
            if inventory:
                inv_rows = []
                for item in inventory:
                    food = session.query(Food).filter(Food.id == item.food_id).first()
                    inv_rows.append({
                        "Food": food.name if food else "?",
                        "Quantity": item.quantity,
                        "Unit": item.unit,
                        "Purchase Date": str(item.purchase_date) if item.purchase_date else "—",
                    })
                st.dataframe(pd.DataFrame(inv_rows), use_container_width=True)
            else:
                st.info("Pantry is empty.")

        with st.form("add_pantry_form"):
            with get_session() as session:
                foods = session.query(Food).all()
                food_names_p = [f.name for f in foods]
            if food_names_p:
                p_food = st.selectbox("Food", food_names_p)
                col_a, col_b = st.columns(2)
                with col_a:
                    p_qty = st.number_input("Quantity", min_value=0.0, step=0.1)
                    p_unit = st.selectbox("Unit", ["g", "kg", "pcs", "ml", "L"])
                with col_b:
                    p_date = st.date_input("Purchase Date", value=datetime.date.today())
                p_submitted = st.form_submit_button("Add to Pantry")

                if p_submitted:
                    with get_session() as session:
                        food_obj = session.query(Food).filter(Food.name == p_food).first()
                        if food_obj:
                            inv = FoodInventory(food_id=food_obj.id, quantity=p_qty, unit=p_unit,
                                                purchase_date=p_date)
                            session.add(inv)
                    st.success("Added to pantry!")
                    st.rerun()

    # ------------------------------------------------------------------
    # Tab 4: Macros & Targets
    # ------------------------------------------------------------------
    with tabs[3]:
        st.subheader("Macros & Targets")

        st.markdown("#### TDEE Calculator")
        with st.form("tdee_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                tdee_weight = st.number_input("Weight (kg)", min_value=30.0, max_value=250.0, value=80.0)
                tdee_height = st.number_input("Height (cm)", min_value=100.0, max_value=250.0, value=175.0)
            with col2:
                tdee_age = st.number_input("Age", min_value=10, max_value=100, value=25)
                tdee_gender = st.selectbox("Gender", ["male", "female"])
            with col3:
                tdee_activity = st.selectbox(
                    "Activity Level",
                    ["sedentary", "lightly_active", "moderately_active", "very_active", "extra_active"],
                    index=2,
                )
            tdee_submitted = st.form_submit_button("Calculate TDEE")

        if tdee_submitted:
            tdee = calculate_tdee(tdee_weight, tdee_height, tdee_age, tdee_gender, tdee_activity)
            st.success(f"**Estimated TDEE: {tdee} kcal/day**")
            st.session_state["tdee_target"] = tdee

        target_calories = st.session_state.get("tdee_target", 2500.0)
        st.markdown(f"**Current Calorie Target:** {target_calories} kcal")

        st.markdown("#### Macro Targets")
        col1, col2, col3 = st.columns(3)
        with col1:
            target_protein = st.number_input("Protein Target (g)", min_value=0.0, value=180.0)
        with col2:
            target_carbs = st.number_input("Carbs Target (g)", min_value=0.0, value=300.0)
        with col3:
            target_fat = st.number_input("Fat Target (g)", min_value=0.0, value=80.0)

        fig_pie = macro_pie_chart(target_protein, target_carbs, target_fat)
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("#### Daily Summary")
        with get_session() as session:
            today_macros = daily_macro_summary(session, datetime.date.today())
            avg_cals = weekly_calorie_average(session)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Calories Today", f"{today_macros['calories']} kcal", f"{today_macros['calories'] - target_calories:+.0f}")
        col2.metric("Protein", f"{today_macros['protein']}g", f"{today_macros['protein'] - target_protein:+.0f}g")
        col3.metric("Carbs", f"{today_macros['carbs']}g", f"{today_macros['carbs'] - target_carbs:+.0f}g")
        col4.metric("Fat", f"{today_macros['fat']}g", f"{today_macros['fat'] - target_fat:+.0f}g")
        st.info(f"7-day Rolling Average: **{avg_cals} kcal/day** (Surplus/Deficit: {avg_cals - target_calories:+.0f} kcal)")

    # ------------------------------------------------------------------
    # Tab 5: Digestion
    # ------------------------------------------------------------------
    with tabs[4]:
        st.subheader("Digestion Timeline")

        dig_date = st.date_input("Date", value=datetime.date.today(), key="dig_date")

        with get_session() as session:
            meals = session.query(Meal).filter(Meal.date == dig_date).all()

        now = datetime.datetime.now()
        active_items = []

        for meal in meals:
            try:
                hour, minute = map(int, meal.time.split(":")) if meal.time else (12, 0)
                meal_start = datetime.datetime.combine(dig_date, datetime.time(hour, minute))
            except (ValueError, AttributeError):
                meal_start = datetime.datetime.combine(dig_date, datetime.time(12, 0))

            for entry in meal.entries:
                if not entry.food:
                    continue
                _, adj_min = estimate_digestion(entry.food.name, entry.food.food_type, entry.amount_grams)
                end_time = meal_start + datetime.timedelta(minutes=adj_min)
                elapsed = (now - meal_start).total_seconds() / 60.0
                pct = min(100.0, max(0.0, (elapsed / adj_min) * 100.0)) if adj_min > 0 else 100.0
                active_items.append({
                    "food_name": f"{entry.food.name} ({entry.amount_grams}g)",
                    "start_time": meal_start,
                    "end_time": end_time,
                    "percent_complete": pct,
                    "adj_minutes": adj_min,
                })

        if not active_items:
            st.info("No meals found for this date. Log meals in the Food Log tab.")
        else:
            st.markdown("### Stomach Queue")
            for item in active_items:
                pct = item["percent_complete"]
                status = "✅ Complete" if pct >= 100 else f"⏳ {pct:.0f}% digested"
                st.markdown(f"**{item['food_name']}** — {status} (est. {item['adj_minutes']} min)")
                st.progress(int(pct))

            st.markdown("### Digestion Gantt Chart")
            gantt_rows = []
            for item in active_items:
                gantt_rows.append({
                    "Food": item["food_name"],
                    "Start": item["start_time"],
                    "Finish": item["end_time"],
                    "% Complete": item["percent_complete"],
                })
            df_gantt = pd.DataFrame(gantt_rows)
            fig = px.timeline(df_gantt, x_start="Start", x_end="Finish", y="Food",
                               color="% Complete", title="Digestion Timeline")
            fig.add_vline(x=now, line_dash="dash", line_color="red", annotation_text="Now")
            st.plotly_chart(fig, use_container_width=True)
