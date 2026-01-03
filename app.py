import os
import json
import streamlit as st
from dotenv import load_dotenv
from typing import Set
from functools import lru_cache

from utils.llm import chat
from utils.retrieval import load_recipes, search
from utils.rules import violates_allergens, violates_diet, propose_substitutions

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Agentic AI System for Smart Personal Cooking Assistant",
    page_icon="🍳",
    layout="wide"
)

# --- Custom CSS for White Background and Black Text ---
st.markdown(
    """
    <style>
    .main {
        background-color: #ffffff;
        color: #000000;
        font-family: 'Helvetica', sans-serif;
    }
    .stApp {
        background-color: #ffffff;
    }
    .title {
        text-align: center;
        font-size: 40px;
        font-weight: bold;
        color: #000000;
        padding: 20px 0;
        border-bottom: 1px solid #e2e8f0;
    }
    .section-header {
        font-size: 24px;
        font-weight: bold;
        color: #000000;
        margin-bottom: 10px;
    }
    .recipe-section {
        color: #000000;
    }
    .footer {
        text-align: center;
        font-size: 12px;
        color: #4a5568;
        padding: 10px 0;
        border-top: 1px solid #e2e8f0;
        margin-top: 20px;
    }
    button {
        background-color: #2d3748;
        color: white;
    }
    pre, code {
        color: #000000 !important;
        background-color: #edf2f7 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Header / Title Section ---
st.markdown('<div class="title">Agentic AI System for Smart Personal Cooking Assistant</div>', unsafe_allow_html=True)

# --- Credits Section ---
st.markdown('<p style="text-align: center; color: #4a5568;">Developed by <b>Suraj Kumar Pandey</b> under mentorship of <b> Dr.Ashok Kumar Yadav </b></p>', unsafe_allow_html=True)

# --- Cache LLM response ---
@lru_cache(maxsize=100)
def cached_chat(system_prompt, user_prompt):
    return chat(system_prompt, user_prompt)

# --- Sidebar: User Profile ---
st.sidebar.header("User Profile")
ethnicity = st.sidebar.selectbox("Cuisine Preference", ["Global", "Indian"], index=0, help="Select 'Indian' for regional Indian recipes or 'Global' for worldwide options including Indian.")
diet = st.sidebar.selectbox("Diet", ["vegetarian", "eggetarian", "vegan", "non-veg"], index=0)
allergies = st.sidebar.multiselect("Allergies", ["nuts", "gluten", "dairy", "eggs"])
dislikes = st.sidebar.text_input("Dislikes (comma separated)", "").lower().split(",") if st.sidebar.text_input("Dislikes (comma separated)", "") else []
tools = st.sidebar.multiselect(
    "Available Tools",
    ["stovetop", "microwave", "oven", "pan", "pressure cooker", "airfryer", "knife", "bowl"],
    default=["stovetop", "pan", "knife", "bowl"]
)
minutes = st.sidebar.slider("Max cooking time (minutes)", 5, 120, 30)
servings = st.sidebar.slider("Servings", 1, 10, 2)

# --- Main: Inventory Input ---
st.markdown('<div class="section-header">Inventory Input</div>', unsafe_allow_html=True)
st.write("Enter your fridge/pantry items (comma-separated) and click 'Find Recipes'.")
inventory_text = st.text_area("Inventory", "paneer, yogurt, onion, capsicum, roti, tomato, lemon")
inventory = set([x.strip().lower() for x in inventory_text.split(",") if x.strip()])

if st.button("🔎 Find Recipes"):
    # 1) PLAN
    user_plan = f"User wants {ethnicity.lower()} recipes using {', '.join(inventory)} within {minutes} minutes for {servings} servings, avoiding dislikes: {dislikes}."

    # 2) RETRIEVE
    ids, sims = search(" ".join(inventory))
    all_recipes = {r["id"]: r for r in load_recipes()}
    candidates = [all_recipes[i] for i in ids if i in all_recipes]

    # 3) CRITIQUE + FILTER (diet/allergens/time/tools/cuisine/dislikes)
    filtered = []
    for r in candidates:
        if r.get("minutes", 9999) > minutes:
            continue
        if violates_diet(r["ingredients"], diet):
            continue
        if violates_allergens(r["ingredients"], set(allergies)):
            continue
        if ethnicity == "Indian" and "indian" not in r.get("tags", []):
            continue
        if any(d in [i.lower() for i in r["ingredients"]] for d in dislikes):
            continue
        filtered.append(r)

    if not filtered:
        st.warning("No perfect matches found. Showing closest candidates with adaptations.")
        filtered = candidates

    # 4) SUBSTITUTIONS
    ranked_payload = []
    for r in filtered:
        subs = propose_substitutions(r["ingredients"], inventory, diet, set(allergies))
        missing = [i for i in r["ingredients"] if i.lower() not in inventory]
        ranked_payload.append((r, subs, missing))

    # 5) LLM RANK + ADAPT
    system = """You are a helpful kitchen assistant. 
Given (inventory, profile, recipe), score suitability 0-100, propose substitutions, 
adapt steps for available tools/time/servings, and explain briefly, considering dislikes.
Return STRICT JSON with keys: score, substituted_ingredients (dict), adapted_steps (list), reason (string)."""

    results = []
    for r, subs, missing in ranked_payload:
        user = f"""
PROFILE:
- ethnicity: {ethnicity}
- diet: {diet}
- allergies: {allergies}
- dislikes: {dislikes}
- tools: {tools}
- max_minutes: {minutes}
- servings: {servings}

INVENTORY: {list(inventory)}

RECIPE:
- title: {r['title']}
- ingredients: {r['ingredients']}
- tools: {r.get('tools', [])}
- minutes: {r.get('minutes')}
- servings: {r.get('servings')}
- steps: {r['steps']}

SUGGESTED_SUBS_FROM_RULES: {subs}
MISSING_INGREDIENTS: {missing}
"""
        try:
            txt = cached_chat(system, user)
            data = json.loads(txt)
            results.append((r, data))
        except Exception as e:
            results.append((r, {
                "score": 50,
                "substituted_ingredients": subs,
                "adapted_steps": r["steps"],
                "reason": f"Fallback: {str(e)}"
            }))

    # 6) DISPLAY ranked recipes (deduplicated)
    seen: Set[str] = set()
    results.sort(key=lambda x: x[1].get("score", 0), reverse=True)

    st.markdown('<div class="section-header">Recommended Recipes</div>', unsafe_allow_html=True)
    for r, data in results:
        if r['title'] in seen:
            continue
        seen.add(r['title'])

        with st.container():
            st.subheader(f"{r['title']} (Score: {data.get('score')})")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Ingredients**")
                st.write(", ".join(r["ingredients"]))
                if data.get("substituted_ingredients"):
                    st.markdown("**Substitutions**")
                    st.json(data["substituted_ingredients"])
            with col2:
                st.markdown("**Why This Recipe?**")
                st.write(data.get("reason", ""))
                st.markdown("**Adapted Steps**")
                for i, step in enumerate(data.get("adapted_steps", r["steps"]), 1):
                    st.write(f"{i}. {step}")

# --- Footer ---

st.markdown('<div class="footer">© 2025 Agentic AI System for Smart Personal Cooking Assistant</div>', unsafe_allow_html=True)


