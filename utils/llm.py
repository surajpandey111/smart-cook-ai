# utils/llm.py
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

CHAT_MODEL = "gemini-2.5-flash"
EMB_MODEL  = "models/text-embedding-004"

def embed_text(text: str):
    resp = genai.embed_content(model=EMB_MODEL, content=text)
    return resp["embedding"]

def chat(system_prompt: str, user_prompt: str):
    model = genai.GenerativeModel(CHAT_MODEL)
    prompt = system_prompt + "\n\n" + user_prompt

    resp = model.generate_content(
        [{"role": "user", "parts": prompt}],
        generation_config={"response_mime_type": "application/json"}
    )

    # Try parsing JSON strictly
    try:
        return resp.text.strip()
    except Exception as e:
        # Fallback: wrap raw text into JSON
        return json.dumps({
            "score": 50,
            "substituted_ingredients": {},
            "adapted_steps": ["Could not parse Gemini output."],
            "reason": "Fallback response."
        })
