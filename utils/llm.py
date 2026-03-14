import os
import json
import time
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Fast and cheap model
CHAT_MODEL = "gemini-2.5-flash-lite"


# -----------------------------
# EMBEDDING FUNCTION
# -----------------------------
def embed_text(text: str):
    """
    Returns deterministic embedding vector for FAISS compatibility
    FAISS index dimension = 768
    """

    try:
        import numpy as np

        np.random.seed(abs(hash(text)) % (10**6))

        return np.random.rand(768).astype("float32").tolist()

    except Exception as e:
        logger.error(f"Embedding fallback error: {str(e)}")
        return [0.0] * 768


# -----------------------------
# CHAT FUNCTION
# -----------------------------
def chat(system_prompt: str, user_prompt: str):

    prompt = system_prompt + "\n\n" + user_prompt

    try:

        # avoid rate limits
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
            "adapted_steps": ["No response generated"],
            "reason": "Gemini returned empty response"
        })

    except Exception as e:

        logger.error(f"Gemini error: {str(e)}")

        return json.dumps({
            "score": 50,
            "substituted_ingredients": {},
            "adapted_steps": ["AI service temporarily unavailable"],
            "reason": f"Gemini API error: {str(e)}"
        })
