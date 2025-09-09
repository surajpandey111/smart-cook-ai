import os, json
import streamlit as st
from dotenv import load_dotenv
from typing import List, Dict, Set

from utils.llm import chat
from utils.retrieval import load_recipes, search
from utils.rules import violates_allergens, violates_diet, propose_substitutions

load_dotenv()
st.set_page_config(page_title="Agentic AI for Smart Cooking", page_icon="🍳", layout="wide")

# --- Sidebar: user profile ---
st.sidebar.header("👤 User Profile")
diet = st.sidebar.selectbox("Diet", ["vegetarian","eggetarian","vegan","non-veg"], index=0)
allergies = st.sidebar.multiselect("Allergies", ["nuts","gluten","dairy","eggs"])
dislikes = st.sidebar.text_input("Dislikes (comma separated)", "")
tools = st.sidebar.multiselect(
    "Available Tools",
    ["stovetop","microwave","oven","pan","pressure cooker","airfryer","knife","bowl"],
    default=["stovetop","pan","knife","bowl"]
)
minutes = st.sidebar.slider("Max cooking time (minutes)", 5, 120, 30)
servings = st.sidebar.slider("Servings", 1, 10, 2)

# --- Main: inventory input ---
st.title("🍳 Agentic AI for Smart Cooking")
st.write("Type your **fridge/pantry inventory** (comma separated), then click *Find Recipes*.")

inventory_text = st.text_area("Inventory", "paneer, yogurt, onion, capsicum, roti, tomato, lemon")
inventory = set([x.strip().lower() for x in inventory_text.split(",") if x.strip()])

if st.button("🔎 Find Recipes"):
    # 1) PLAN
    user_plan = f"User wants recipes using {', '.join(inventory)} within {minutes} minutes for {servings} servings."

    # 2) RETRIEVE
    ids, sims = search(" ".join(inventory))
    all_recipes = {r["id"]: r for r in load_recipes()}
    candidates = [all_recipes[i] for i in ids if i in all_recipes]

    # 3) CRITIQUE + FILTER (diet/allergens/time/tools)
    filtered = []
    for r in candidates:
        if r.get("minutes", 9999) > minutes:
            continue
        if violates_diet(r["ingredients"], diet):
            continue
        if violates_allergens(r["ingredients"], set(allergies)):
            continue
        filtered.append(r)

    if not filtered:
        st.warning("No perfect matches; showing closest candidates with adaptation.")
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
adapt steps for available tools/time/servings, and explain briefly.
Return STRICT JSON with keys: score, substituted_ingredients (dict), adapted_steps (list), reason (string)."""

    results = []
    for r, subs, missing in ranked_payload:
        user = f"""
PROFILE:
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
            txt = chat(system, user)
            data = json.loads(txt)   # parse Gemini response as JSON
            results.append((r, data))
        except Exception as e:
            # fallback minimal answer
            results.append((r, {
                "score": 50,
                "substituted_ingredients": subs,
                "adapted_steps": r["steps"],
                "reason": f"Fallback: {str(e)}"
            }))

    # 6) DISPLAY ranked recipes (deduplicated)
    seen: Set[str] = set()
    results.sort(key=lambda x: x[1].get("score", 0), reverse=True)

    for r, data in results:
        if r['title'] in seen:
            continue  # skip duplicates
        seen.add(r['title'])

        with st.container(border=True):
            st.subheader(f"{r['title']} — score {data.get('score')}")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Ingredients**")
                st.write(", ".join(r["ingredients"]))
                if data.get("substituted_ingredients"):
                    st.markdown("**Substitutions**")
                    st.json(data["substituted_ingredients"])
            with col2:
                st.markdown("**Why this recipe**")
                st.write(data.get("reason",""))
                st.markdown("**Adapted Steps**")
                for i, step in enumerate(data.get("adapted_steps", r["steps"]), 1):
                    st.write(f"{i}. {step}")
