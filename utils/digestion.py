"""
Digestion time estimates by food type and specific food overrides.
"""

DIGESTION_TIMES = {
    "simple_carb": 60,
    "complex_carb": 120,
    "protein": 180,
    "fat": 300,
    "vegetable": 90,
    "fruit": 60,
    "dairy": 150,
}

FOOD_SPECIFIC_OVERRIDES = {
    "white rice": 90,
    "oats": 120,
    "chicken breast": 150,
    "red meat": 240,
    "eggs": 120,
    "protein shake": 90,
    "sweet potato": 150,
    "banana": 45,
    "white bread": 60,
    "whole grain bread": 120,
    "brown rice": 150,
    "pasta": 120,
    "salmon": 180,
    "tuna": 150,
    "greek yogurt": 90,
    "cottage cheese": 120,
    "milk": 120,
    "broccoli": 60,
    "spinach": 45,
    "apple": 60,
    "orange": 60,
    "almonds": 210,
    "peanut butter": 240,
    "olive oil": 300,
    "avocado": 210,
    "beef steak": 270,
    "pork": 240,
    "turkey breast": 150,
    "lentils": 150,
    "beans": 150,
}


def estimate_digestion(food_name: str, food_type: str, amount_grams: float) -> tuple:
    """Estimate digestion time for a food item.

    Returns:
        (base_digestion_minutes, adjusted_digestion_minutes)
        The adjusted value scales slightly with portion size (larger meals digest a bit slower).
    """
    normalized = food_name.strip().lower()

    base_minutes = FOOD_SPECIFIC_OVERRIDES.get(normalized, DIGESTION_TIMES.get(food_type, 120))

    # Scale adjustment: every 100g above a 200g baseline adds ~5% more time
    baseline_grams = 200.0
    if amount_grams > baseline_grams:
        scale_factor = 1.0 + 0.05 * ((amount_grams - baseline_grams) / 100.0)
    else:
        scale_factor = 1.0

    adjusted_minutes = int(base_minutes * scale_factor)
    return base_minutes, adjusted_minutes
