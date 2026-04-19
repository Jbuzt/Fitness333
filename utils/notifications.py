"""
Alert and reminder helper functions.
"""

import datetime


def get_low_stock_supplements(session, threshold_days: int = 7) -> list:
    """Return supplements that are running low (estimated days remaining < threshold_days).

    Args:
        session: SQLAlchemy session
        threshold_days: Warn when estimated days remaining is below this value

    Returns:
        List of dicts with supplement info and days_remaining
    """
    from db.models import Supplement

    supplements = session.query(Supplement).all()
    low_stock = []
    for s in supplements:
        if s.daily_dose and s.daily_dose > 0:
            days_remaining = s.quantity / s.daily_dose
        else:
            days_remaining = float("inf")

        if days_remaining < threshold_days:
            low_stock.append({
                "id": s.id,
                "name": s.name,
                "quantity": s.quantity,
                "unit": s.unit,
                "days_remaining": round(days_remaining, 1),
            })
    return low_stock


def get_active_compounds(session) -> list:
    """Return currently active gear compounds (start_date <= today <= end_date, or no end_date).

    Args:
        session: SQLAlchemy session

    Returns:
        List of Compound ORM objects
    """
    from db.models import Compound

    today = datetime.date.today()
    compounds = session.query(Compound).all()
    active = []
    for c in compounds:
        started = c.start_date is None or c.start_date <= today
        not_ended = c.end_date is None or c.end_date >= today
        if started and not_ended:
            active.append(c)
    return active


def get_todays_meals(session) -> list:
    """Return meals logged today.

    Args:
        session: SQLAlchemy session

    Returns:
        List of Meal ORM objects
    """
    from db.models import Meal

    today = datetime.date.today()
    return session.query(Meal).filter(Meal.date == today).all()


def get_todays_workout(session):
    """Return the workout session for today, or None.

    Args:
        session: SQLAlchemy session

    Returns:
        WorkoutSession ORM object or None
    """
    from db.models import WorkoutSession

    today = datetime.date.today()
    return session.query(WorkoutSession).filter(WorkoutSession.date == today).first()
