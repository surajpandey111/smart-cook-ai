import os
import json
import streamlit as st
from dotenv import load_dotenv
from typing import Set
from functools import lru_cache

from utils.llm import chat
from utils.retrieval import load_recipes, search
from utils.rules import violates_allergens, violates_diet, propose_substitutions

load_dotenv()

st.set_page_config(
    page_title="Agentic AI System for Smart Personal Cooking Assistant",
    page_icon="🍳",
    layout="wide"
)

# ---------- UI STYLE ----------
st.markdown("""
<style>
.main {background-color:#ffffff;color:#000}
.stApp {background-color:#ffffff}
.title {text-align:center;font-size:40px;font-weight:bold;padding:20px}
.section-header {font-size:24px;font-weight:bold;margin-bottom:10px}
.footer {text-align:center;font-size:12px;margin-top:20px}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">Agentic AI System for Smart Personal Cooking Assistant</div>', unsafe_allow_html=True)

st.markdown('<p style="text-align:center;">Developed by <b>Suraj Kumar Pandey</b> under mentorship of <b>Dr. Ashok Kumar Yadav</b></p>', unsafe_allow_html=True)


# ---------- CACHE ----------
@lru_cache(maxsize=100)
def cached_chat(system_prompt, user_prompt):
    return chat(system_prompt, user_prompt)


# ---------- SIDEBAR ----------
st.sidebar.header("User Profile")

ethnicity = st.sidebar.selectbox("Cuisine Preference", ["Global","Indian"])
diet = st.sidebar.selectbox("Diet", ["vegetarian","eggetarian","vegan","non-veg"])
allergies = st.sidebar.multiselect("Allergies", ["nuts","gluten","dairy","eggs"])

dislike_text = st.sidebar.text_input("Dislikes (comma separated)")
dislikes = [x.strip().lower() for x in dislike_text.split(",") if x]

tools = st.sidebar.multiselect(
    "Available Tools",
    ["stovetop","microwave","oven","pan","pressure cooker","airfryer","knife","bowl"],
    default=["stovetop","pan","knife","bowl"]
)

minutes = st.sidebar.slider("Max cooking time",5,120,30)
servings = st.sidebar.slider("Servings",1,10,2)


# ---------- INVENTORY ----------
st.markdown('<div class="section-header">Inventory Input</div>', unsafe_allow_html=True)

inventory_text = st.text_area(
    "Enter ingredients",
    "paneer, yogurt, onion, capsicum, roti, tomato, lemon"
)

inventory = set([x.strip().lower() for x in inventory_text.split(",") if x])


# ---------- BUTTON ----------
if st.button("🔎 Find Recipes"):

    # RETRIEVE
    ids, sims = search(" ".join(inventory), k=3)

    all_recipes = {r["id"]: r for r in load_recipes()}
    candidates = [all_recipes[i] for i in ids if i in all_recipes]

    filtered = []

    for r in candidates:

        if r.get("minutes",9999) > minutes:
            continue

        if violates_diet(r["ingredients"], diet):
            continue

        if violates_allergens(r["ingredients"], set(allergies)):
            continue

        if ethnicity=="Indian" and "indian" not in r.get("tags",[]):
            continue

        if any(d in [i.lower() for i in r["ingredients"]] for d in dislikes):
            continue

        filtered.append(r)

    if not filtered:
        st.warning("No perfect matches found. Showing closest recipes.")
        filtered = candidates

    # ---------- LLM RANK ----------
    system = """
You are a cooking assistant.

Return JSON:
{
score:int,
substituted_ingredients:dict,
adapted_steps:list,
reason:string
}
"""

    results = []

    for r in filtered[:3]:

        subs = propose_substitutions(r["ingredients"], inventory, diet, set(allergies))

        missing = [i for i in r["ingredients"] if i.lower() not in inventory]

        user_prompt = f"""
PROFILE
diet:{diet}
tools:{tools}
time:{minutes}

INVENTORY
{inventory}

RECIPE
title:{r['title']}
ingredients:{r['ingredients']}
steps:{r['steps']}

MISSING
{missing}
"""

        try:

            txt = cached_chat(system,user_prompt)

            data = json.loads(txt)

        except:

            data = {
                "score":50,
                "substituted_ingredients":subs,
                "adapted_steps":r["steps"],
                "reason":"Fallback recipe"
            }

        results.append((r,data))

    results.sort(key=lambda x:x[1].get("score",0),reverse=True)

    # ---------- DISPLAY ----------
    st.markdown('<div class="section-header">Recommended Recipes</div>', unsafe_allow_html=True)

    seen: Set[str] = set()

    for r,data in results:

        if r["title"] in seen:
            continue

        seen.add(r["title"])

        st.subheader(f"{r['title']} (Score {data.get('score')})")

        col1,col2 = st.columns(2)

        with col1:

            st.markdown("**Ingredients**")
            st.write(", ".join(r["ingredients"]))

            if data.get("substituted_ingredients"):
                st.markdown("**Substitutions**")
                st.json(data["substituted_ingredients"])

        with col2:

            st.markdown("**Why This Recipe?**")
            st.write(data.get("reason",""))

            st.markdown("**Steps**")

            for i,step in enumerate(data.get("adapted_steps",r["steps"]),1):
                st.write(f"{i}. {step}")


# ---------- FOOTER ----------
st.markdown('<div class="footer">© 2025 Smart Cooking AI</div>', unsafe_allow_html=True)
