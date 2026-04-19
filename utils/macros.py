"""
Macro and TDEE calculation helpers.
"""

import datetime
from typing import Optional


ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "extra_active": 1.9,
}


def calculate_tdee(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str = "moderately_active",
) -> float:
    """Calculate TDEE using Mifflin-St Jeor BMR × activity multiplier.

    Args:
        weight_kg: Body weight in kilograms
        height_cm: Height in centimetres
        age: Age in years
        gender: 'male' or 'female'
        activity_level: One of the ACTIVITY_MULTIPLIERS keys

    Returns:
        TDEE in kcal/day
    """
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
    return round(bmr * multiplier, 1)


def calculate_meal_macros(meal_entries) -> dict:
    """Calculate total macros for a list of MealEntry ORM objects.

    Args:
        meal_entries: list of MealEntry objects (with .food and .amount_grams)

    Returns:
        dict with keys: calories, protein, carbs, fat, fiber, sugar (all floats)
    """
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0, "sugar": 0.0}
    for entry in meal_entries:
        food = entry.food
        if food is None:
            continue
        amount = entry.amount_grams
        if not amount or amount <= 0:
            continue
        ratio = amount / 100.0
        totals["calories"] += food.calories_per_100g * ratio
        totals["protein"] += food.protein_per_100g * ratio
        totals["carbs"] += food.carbs_per_100g * ratio
        totals["fat"] += food.fat_per_100g * ratio
        totals["fiber"] += food.fiber_per_100g * ratio
        totals["sugar"] += food.sugar_per_100g * ratio
    return {k: round(v, 1) for k, v in totals.items()}


def daily_macro_summary(session, date: datetime.date) -> dict:
    """Query all meals for a date and return full macro breakdown.

    Args:
        session: SQLAlchemy session
        date: The date to summarise

    Returns:
        dict with macro totals
    """
    from db.models import Meal, MealEntry

    meals = session.query(Meal).filter(Meal.date == date).all()
    all_entries = []
    for meal in meals:
        all_entries.extend(meal.entries)
    return calculate_meal_macros(all_entries)


def weekly_calorie_average(session, end_date: Optional[datetime.date] = None) -> float:
    """Calculate 7-day rolling average calories ending on end_date.

    Args:
        session: SQLAlchemy session
        end_date: Last date (defaults to today)

    Returns:
        Average daily calories over the last 7 days
    """
    if end_date is None:
        end_date = datetime.date.today()

    start_date = end_date - datetime.timedelta(days=6)
    daily_totals = []
    current = start_date
    while current <= end_date:
        summary = daily_macro_summary(session, current)
        daily_totals.append(summary.get("calories", 0.0))
        current += datetime.timedelta(days=1)

    if not daily_totals:
        return 0.0
    return round(sum(daily_totals) / len(daily_totals), 1)
