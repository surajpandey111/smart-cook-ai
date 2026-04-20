import os
import json
import re
import streamlit as st
from dotenv import load_dotenv
from functools import lru_cache

from utils.llm import chat
from utils.retrieval import load_recipes, search
from utils.rules import violates_allergens, violates_diet
from utils.agent import decide_strategy

load_dotenv()

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Smart Cooking AI",
    page_icon="🍳",
    layout="wide"
)

# ---------------- HEADER ----------------
st.markdown("""
<h1 style='text-align:center;'>🍳 Smart Cooking AI</h1>
<p style='text-align:center;color:gray;font-size:18px;'>
Agentic AI System for Smart Personal Cooking Assistant
</p>
""", unsafe_allow_html=True)

# ---------------- JSON EXTRACTOR ----------------
def extract_json(text):
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except:
        pass
    return None

# ---------------- CACHE ----------------
@lru_cache(maxsize=100)
def cached_chat(system_prompt, user_prompt):
    return chat(system_prompt, user_prompt)

# ---------------- SIDEBAR ----------------
st.sidebar.title("User Profile")

# ✅ NEW: CUISINE FILTER
cuisine = st.sidebar.selectbox(
    "Cuisine Preference",
    ["All", "Indian", "Global"]
)

diet = st.sidebar.selectbox("Diet", ["vegetarian","eggetarian","vegan","non-veg"])

allergies = st.sidebar.multiselect("Allergies", ["nuts","gluten","dairy","eggs"])

tools = st.sidebar.multiselect(
    "Available Tools",
    ["stovetop","microwave","oven","pan","knife","bowl"],
    default=["stovetop","pan"]
)

minutes = st.sidebar.slider("Max Cooking Time", 5, 120, 30)

# ---------------- INVENTORY ----------------
st.subheader("Inventory Input")

inventory_text = st.text_area(
    "Enter ingredients",
    "paneer, yogurt, onion, capsicum, roti, tomato, lemon"
)

inventory = set(x.strip().lower() for x in inventory_text.split(",") if x)

def clean_ing(x):
    return x.lower().split()[0]

# ---------------- BUTTON ----------------
if st.button("🔍 Find Recipes"):

    strategy = decide_strategy(inventory, diet, set(allergies))

    # ---------------- CREATIVE MODE ----------------
    if strategy == "creative_generation":

        st.warning("⚡ Generating recipe from scratch...")

        system = """
You are a professional chef.

Create a simple practical recipe using given ingredients.
"""

        user_prompt = f"""
Ingredients: {inventory}
Diet: {diet}
Time: {minutes}
Tools: {tools}
"""

        result = chat(system, user_prompt)
        st.write(result)
        st.stop()

    # ---------------- RETRIEVAL (IMPROVED QUERY) ----------------
    query = " ".join(inventory) + f" {diet} {cuisine}"
    ids, sims = search(query, k=5)

    all_recipes = {r["id"]: r for r in load_recipes()}
    candidates = [all_recipes[i] for i in ids if i in all_recipes]

    filtered = []

    # ---------------- FILTERING ----------------
    for r in candidates:

        # ⏱ TIME FILTER
        if r.get("minutes", 9999) > minutes:
            continue

        # 🥗 DIET
        if violates_diet(r["ingredients"], diet):
            continue

        # ⚠️ ALLERGY
        if violates_allergens(r["ingredients"], set(allergies)):
            continue

        # 🌍 CUISINE FILTER (NEW)
        if cuisine != "All":
            tags = [t.lower() for t in r.get("tags", [])]

            if cuisine.lower() == "indian" and "indian" not in tags:
                continue

            if cuisine.lower() == "global" and "indian" in tags:
                continue

        filtered.append(r)

    if not filtered:
        filtered = candidates

    # ---------------- LLM PROMPT ----------------
    system = """
You are a professional chef AI.

Your job:
- Adapt recipe using available ingredients
- Replace missing ingredients smartly
- Simplify cooking steps
- Make it practical for real cooking

STRICT:
- Return ONLY valid JSON
- No extra text

FORMAT:
{
"score": int (0-100),
"substituted_ingredients": {"original":"replacement"},
"adapted_steps": ["step1","step2"],
"reason": "short explanation"
}
"""

    results = []

    # ---------------- PROCESS ----------------
    for idx, r in enumerate(filtered[:1]):  # keep 1 for quota safety

        missing = [i for i in r["ingredients"] if clean_ing(i) not in inventory]

        user_prompt = f"""
Diet: {diet}
Cuisine: {cuisine}
Tools: {tools}
Time: {minutes}

Inventory: {inventory}

Recipe:
{r}

Missing:
{missing}
"""

        txt = cached_chat(system, user_prompt)

        data = extract_json(txt)

        if not data:
            st.warning("⚠️ AI parsing failed")
            st.code(txt)

            data = {
                "score": 50,
                "substituted_ingredients": {},
                "adapted_steps": r["steps"],
                "reason": "Fallback used"
            }

        sim_score = sims[idx]
        inv_match = len(set(clean_ing(i) for i in r["ingredients"]) & inventory) / len(r["ingredients"])
        llm_score = data.get("score", 50) / 100

        final_score = 0.5 * sim_score + 0.3 * llm_score + 0.2 * inv_match

        results.append((r, data, final_score))

    results.sort(key=lambda x: x[2], reverse=True)

    # ---------------- DISPLAY ----------------
    st.subheader("🍽️ Recommended Recipes")

    for r, data, score in results:

        with st.container():

            st.markdown(f"### {r['title']}")

            # 🌍 SHOW TAGS
            tags = ", ".join(r.get("tags", []))
            st.caption(f"🌍 {tags}")

            col1, col2 = st.columns([2,1])

            with col1:
                st.markdown("**🧾 Ingredients**")
                st.write(", ".join(r["ingredients"]))

                st.markdown("**👨‍🍳 Steps**")
                for i, s in enumerate(data.get("adapted_steps", r["steps"]), 1):
                    st.write(f"{i}. {s}")

            with col2:
                st.metric("Score", int(score * 100))

                missing = [i for i in r["ingredients"] if clean_ing(i) not in inventory]

                st.markdown("**❌ Missing**")
                st.write(missing)

                st.markdown("**🔁 Substitutions**")
                st.write(data.get("substituted_ingredients", {}))

            st.markdown("**🧠 Why this recipe?**")
            st.info(data.get("reason", "No explanation"))

            st.progress(data.get("score", 50)/100)

            st.divider()