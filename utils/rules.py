from typing import List, Dict, Tuple, Set

# very small starter maps; extend these
ALLERGENS = {"nuts","gluten","dairy","eggs"}
ANIMAL_PRODUCTS = {"chicken","meat","fish","egg","eggs","paneer","yogurt","milk","ghee","butter"}

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

def violates_diet(ingredients: List[str], diet: str) -> bool:
    items = set(map(str.lower, ingredients))
    if diet == "vegan":
        return any(x in items for x in ANIMAL_PRODUCTS if x not in {"milk","yogurt","butter","ghee"}) or "paneer" in items or "eggs" in items
    if diet == "vegetarian":
        return any(x in items for x in {"chicken","meat","fish"})
    if diet == "eggetarian":
        return any(x in items for x in {"chicken","meat","fish"})
    return False  # non-veg

def violates_allergens(ingredients: List[str], allergens: Set[str]) -> bool:
    items = set(map(str.lower, ingredients))
    if "eggs" in allergens and "eggs" in items: return True
    if "dairy" in allergens and any(x in items for x in {"milk","butter","ghee","yogurt","paneer"}): return True
    if "gluten" in allergens and any(x in items for x in {"wheat","roti","bread","maida"}): return True
    if "nuts" in allergens and any("nut" in x for x in items): return True
    return False

def propose_substitutions(ingredients: List[str], inventory: Set[str], diet: str, allergens: Set[str]) -> Dict[str,str]:
    subs = {}
    inv_low = set(map(str.lower, inventory))
    ingr_low = list(map(str.lower, ingredients))
    for ing in ingr_low:
        if ing not in inv_low:
            # diet-based
            if diet in SUBS and ing in SUBS[diet]:
                subs[ing] = SUBS[diet][ing]
        # allergen-based or catch-all could go here
    return subs