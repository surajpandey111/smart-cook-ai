from typing import List, Dict, Set

# -----------------------------
# CONSTANTS
# -----------------------------
ALLERGENS = {"nuts","gluten","dairy","eggs"}

ANIMAL_PRODUCTS = {
    "chicken","meat","fish","egg","eggs",
    "paneer","yogurt","milk","ghee","butter"
}

SUBS = {
    "vegan": {
        "paneer": "tofu",
        "yogurt": "soy yogurt",
        "milk": "almond milk",
        "butter": "vegetable oil",
        "ghee": "vegetable oil",
        "eggs": "besan-water mix"
    },
    "gluten-free": {
        "roti": "corn tortilla"
    }
}

# -----------------------------
# HELPERS
# -----------------------------
def normalize(text):
    return text.lower().strip()

def contains_any(items, keywords):
    return any(any(k in item for k in keywords) for item in items)

# -----------------------------
# DIET CHECK
# -----------------------------
def violates_diet(ingredients: List[str], diet: str) -> bool:

    items = [normalize(i) for i in ingredients]

    if diet == "vegan":
        if contains_any(items, ANIMAL_PRODUCTS):
            return True

    if diet == "vegetarian":
        if contains_any(items, {"chicken","meat","fish"}):
            return True

    if diet == "eggetarian":
        if contains_any(items, {"chicken","meat","fish"}):
            return True

    return False


# -----------------------------
# ALLERGEN CHECK
# -----------------------------
def violates_allergens(ingredients: List[str], allergens: Set[str]) -> bool:

    items = [normalize(i) for i in ingredients]

    if "eggs" in allergens and contains_any(items, {"egg"}):
        return True

    if "dairy" in allergens and contains_any(items, {"milk","butter","ghee","yogurt","paneer"}):
        return True

    if "gluten" in allergens and contains_any(items, {"wheat","roti","bread","maida"}):
        return True

    if "nuts" in allergens and contains_any(items, {"nut","almond","cashew"}):
        return True

    return False


# -----------------------------
# SUBSTITUTIONS
# -----------------------------
def propose_substitutions(
    ingredients: List[str],
    inventory: Set[str],
    diet: str,
    allergens: Set[str]
) -> Dict[str,str]:

    subs = {}

    inv_low = set(normalize(i) for i in inventory)
    ingr_low = [normalize(i) for i in ingredients]

    for ing in ingr_low:

        if ing not in inv_low:

            # diet-based substitutions
            if diet in SUBS and ing in SUBS[diet]:
                subs[ing] = SUBS[diet][ing]

    return subs