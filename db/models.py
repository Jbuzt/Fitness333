from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, Enum
)
from sqlalchemy.orm import relationship, declarative_base
import enum
import datetime

Base = declarative_base()


# ---------------------------------------------------------------------------
# Supplementation
# ---------------------------------------------------------------------------

class Supplement(Base):
    __tablename__ = "supplements"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    quantity = Column(Float, default=0.0)
    unit = Column(String(20), default="g")  # kg/g/caps/ml/tabs
    purchase_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    daily_dose = Column(Float, default=0.0)
    dose_unit = Column(String(20), default="g")
    dose_timing = Column(String(30), default="morning")  # morning/pre-workout/post-workout/night/other
    cost_per_unit = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    logs = relationship("SupplementLog", back_populates="supplement", cascade="all, delete-orphan")


class SupplementLog(Base):
    __tablename__ = "supplement_logs"

    id = Column(Integer, primary_key=True)
    supplement_id = Column(Integer, ForeignKey("supplements.id"), nullable=False)
    date = Column(Date, nullable=False, default=datetime.date.today)
    amount_used = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    supplement = relationship("Supplement", back_populates="logs")


# ---------------------------------------------------------------------------
# Diet / Food
# ---------------------------------------------------------------------------

class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    calories_per_100g = Column(Float, default=0.0)
    protein_per_100g = Column(Float, default=0.0)
    carbs_per_100g = Column(Float, default=0.0)
    fat_per_100g = Column(Float, default=0.0)
    fiber_per_100g = Column(Float, default=0.0)
    sugar_per_100g = Column(Float, default=0.0)
    digestion_time_minutes = Column(Integer, default=120)
    food_type = Column(String(30), default="complex_carb")  # simple_carb/complex_carb/protein/fat/vegetable/fruit/dairy

    inventory = relationship("FoodInventory", back_populates="food", cascade="all, delete-orphan")
    meal_entries = relationship("MealEntry", back_populates="food")


class FoodInventory(Base):
    __tablename__ = "food_inventory"

    id = Column(Integer, primary_key=True)
    food_id = Column(Integer, ForeignKey("foods.id"), nullable=False)
    quantity = Column(Float, default=0.0)
    unit = Column(String(20), default="g")
    purchase_date = Column(Date, nullable=True)

    food = relationship("Food", back_populates="inventory")


class Meal(Base):
    __tablename__ = "meals"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, default=datetime.date.today)
    time = Column(String(10), nullable=True)  # HH:MM
    meal_name = Column(String(30), default="lunch")  # breakfast/lunch/dinner/snack/pre-workout/post-workout
    notes = Column(Text, nullable=True)

    entries = relationship("MealEntry", back_populates="meal", cascade="all, delete-orphan")


class MealEntry(Base):
    __tablename__ = "meal_entries"

    id = Column(Integer, primary_key=True)
    meal_id = Column(Integer, ForeignKey("meals.id"), nullable=False)
    food_id = Column(Integer, ForeignKey("foods.id"), nullable=False)
    amount_grams = Column(Float, default=100.0)

    meal = relationship("Meal", back_populates="entries")
    food = relationship("Food", back_populates="meal_entries")


# ---------------------------------------------------------------------------
# Workout
# ---------------------------------------------------------------------------

class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, default=datetime.date.today)
    phase = Column(String(20), default="maintenance")  # bulk/cut/maintenance/recomp
    notes = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=60)
    overall_rpe = Column(Float, nullable=True)

    sets = relationship("ExerciseSet", back_populates="session", cascade="all, delete-orphan")


class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    muscle_group = Column(String(30), default="full_body")  # chest/back/legs/shoulders/arms/core/full_body
    equipment = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)

    sets = relationship("ExerciseSet", back_populates="exercise")


class ExerciseSet(Base):
    __tablename__ = "exercise_sets"

    id = Column(Integer, primary_key=True)
    workout_session_id = Column(Integer, ForeignKey("workout_sessions.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    set_number = Column(Integer, default=1)
    reps = Column(Integer, default=10)
    weight_kg = Column(Float, default=0.0)
    rpe = Column(Float, nullable=True)
    rest_seconds = Column(Integer, default=90)
    notes = Column(Text, nullable=True)

    session = relationship("WorkoutSession", back_populates="sets")
    exercise = relationship("Exercise", back_populates="sets")


# ---------------------------------------------------------------------------
# Gear (Steroids / Compounds)
# ---------------------------------------------------------------------------

class Compound(Base):
    __tablename__ = "compounds"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(20), default="anabolic")  # anabolic/peptide/sarm/other
    ester = Column(String(50), nullable=True)
    dose_mg = Column(Float, default=0.0)
    frequency = Column(String(20), default="weekly")  # daily/eod/e3d/twice_weekly/weekly
    administration = Column(String(20), default="injection")  # injection/oral/topical
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    inventory_ml = Column(Float, default=0.0)
    concentration_mg_per_ml = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    injection_logs = relationship("InjectionLog", back_populates="compound", cascade="all, delete-orphan")


class InjectionLog(Base):
    __tablename__ = "injection_logs"

    id = Column(Integer, primary_key=True)
    compound_id = Column(Integer, ForeignKey("compounds.id"), nullable=False)
    date = Column(Date, nullable=False, default=datetime.date.today)
    time = Column(String(10), nullable=True)
    dose_mg = Column(Float, default=0.0)
    site = Column(String(30), default="right_glute")  # left_glute/right_glute/left_quad/right_quad/left_delt/right_delt/other
    notes = Column(Text, nullable=True)

    compound = relationship("Compound", back_populates="injection_logs")


class InsulinLog(Base):
    __tablename__ = "insulin_logs"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, default=datetime.date.today)
    time = Column(String(10), nullable=True)
    units = Column(Float, default=0.0)
    insulin_type = Column(String(20), default="fast_acting")  # fast_acting/slow_acting/mixed
    timing_relative_to_meal = Column(String(20), default="post_meal")  # pre_meal/post_meal/fasted/with_meal
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Blood Work
# ---------------------------------------------------------------------------

class BloodWorkResult(Base):
    __tablename__ = "blood_work_results"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, default=datetime.date.today)
    marker_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(30), nullable=True)
    reference_min = Column(Float, nullable=True)
    reference_max = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Body Metrics
# ---------------------------------------------------------------------------

class BodyMetric(Base):
    __tablename__ = "body_metrics"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, default=datetime.date.today)
    weight_kg = Column(Float, nullable=True)
    body_fat_percent = Column(Float, nullable=True)
    muscle_mass_kg = Column(Float, nullable=True)
    waist_cm = Column(Float, nullable=True)
    chest_cm = Column(Float, nullable=True)
    left_arm_cm = Column(Float, nullable=True)
    right_arm_cm = Column(Float, nullable=True)
    left_leg_cm = Column(Float, nullable=True)
    right_leg_cm = Column(Float, nullable=True)
    neck_cm = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Wellbeing
# ---------------------------------------------------------------------------

class WellbeingLog(Base):
    __tablename__ = "wellbeing_logs"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, default=datetime.date.today)
    mood_score = Column(Integer, nullable=True)       # 1-10
    energy_score = Column(Integer, nullable=True)     # 1-10
    sleep_hours = Column(Float, nullable=True)
    sleep_quality = Column(Integer, nullable=True)    # 1-10
    side_effects = Column(Text, nullable=True)
    libido_score = Column(Integer, nullable=True)     # 1-10
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    unit = Column(String(30), nullable=True)
    deadline = Column(Date, nullable=True)
    status = Column(String(20), default="active")  # active/completed/paused
    created_at = Column(Date, default=datetime.date.today)


# ---------------------------------------------------------------------------
# PCT
# ---------------------------------------------------------------------------

class PCTProtocol(Base):
    __tablename__ = "pct_protocols"

    id = Column(Integer, primary_key=True)
    cycle_end_date = Column(Date, nullable=True)
    compound_name = Column(String(50), nullable=False)  # Nolvadex/Clomid/HCG/Aromasin/other
    dose_mg = Column(Float, default=0.0)
    frequency = Column(String(20), default="daily")
    duration_weeks = Column(Integer, default=4)
    start_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
