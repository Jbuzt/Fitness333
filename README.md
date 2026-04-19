# Fitness Tracker 🏋️

A personal fitness tracking system built with **Python + Streamlit + SQLite (SQLAlchemy) + Plotly**.

## Features

| Module | Description |
|---|---|
| 🏠 Dashboard | Today's summary: calories, meals, workout status, active compounds, alerts |
| 💊 Supplementation | Inventory, usage logs, timing schedule, analytics & cost tracker |
| 🥗 Diet | Food log, meal timeline, pantry, macro/TDEE targets, digestion tracker |
| 🏋️ Workout | Workout logger, routine builder, PR tracker, weekly volume analysis |
| 💉 Gear | Active cycle overview, injection & insulin logs, cycle planner (Gantt), inventory |
| 📏 Body Metrics | Weight/body-fat log, trend charts with 7-day MA, radar measurement chart |
| 🩸 Blood Work | Lab result logger, colour-coded marker dashboard, trend charts with reference bands |
| 📋 PCT Planner | Protocol builder, active PCT countdown, natty recovery progress tracker |
| 😴 Wellbeing | Daily mood/energy/sleep/libido log, trend charts, side-effect journal |
| 🎯 Goals | Goal setting with progress bars, deadline countdowns, status management |

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app creates a `fitness_tracker.db` SQLite database in the project root on first run.

## Project Structure

```
fitness_tracker/
├── app.py                  # Streamlit entry point + sidebar navigation
├── db/
│   ├── database.py         # SQLAlchemy engine, session, Base, init_db()
│   └── models.py           # All ORM models
├── modules/                # One render() function per page
│   ├── supplementation.py
│   ├── diet.py
│   ├── workout.py
│   ├── gear.py
│   ├── body_metrics.py
│   ├── blood_work.py
│   ├── pct.py
│   ├── wellbeing.py
│   └── goals.py
├── components/
│   └── charts.py           # Reusable Plotly chart functions
├── utils/
│   ├── macros.py           # Macro / TDEE calculations
│   ├── digestion.py        # Digestion timeline estimation
│   └── notifications.py    # Alert / reminder helpers
├── requirements.txt
└── README.md
```

## Expanding the System

Each page module is a standalone `render()` function — add a new file under `modules/`, import it in `app.py`, and add a sidebar button. The SQLAlchemy models in `db/models.py` can be extended with new tables at any time; run `init_db()` to apply the schema changes.
