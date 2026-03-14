import os
import json
import time
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# Gemini Client
# -----------------------------
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Best stable fast model
CHAT_MODEL = "gemini-1.5-flash"


# ------------------------------------------------
# EMBEDDING FUNCTION
# (fallback dummy because embeddings done in FAISS)
# ------------------------------------------------
def embed_text(text: str):
    """
    This returns a dummy vector so FAISS query does not crash.
    You should use local embeddings for production.
    """

    try:
        import numpy as np
        np.random.seed(abs(hash(text)) % (10**6))
        return np.random.rand(384).tolist()

    except Exception as e:
        logger.error(f"Embedding fallback error: {str(e)}")
        return [0.0] * 384


# -----------------------------
# CHAT FUNCTION
# -----------------------------
def chat(system_prompt: str, user_prompt: str):

    prompt = system_prompt + "\n\n" + user_prompt

    try:

        # prevent rate limits
        time.sleep(1)

        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt
        )

        if hasattr(response, "text"):
            return response.text

        return json.dumps({
            "score": 50,
            "substituted_ingredients": {},
            "adapted_steps": ["No response generated."],
            "reason": "Gemini returned empty response"
        })

    except Exception as e:

        logger.error(f"Gemini error: {str(e)}")

        return json.dumps({
            "score": 50,
            "substituted_ingredients": {},
            "adapted_steps": ["AI service temporarily unavailable."],
            "reason": f"Gemini API error: {str(e)}"
        })
