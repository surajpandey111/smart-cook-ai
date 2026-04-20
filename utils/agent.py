def decide_strategy(inventory, diet, allergies):

    if len(inventory) < 3:
        return "creative_generation"

    if diet == "vegan":
        return "strict_filter"

    if len(allergies) > 1:
        return "strict_filter"

    return "normal"