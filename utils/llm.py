import os
import json
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Use Flash-Lite model
CHAT_MODEL = "gemini-2.0-flash-lite"

# Safe embedding model for public Gemini API
EMB_MODEL = "embedding-001"


def embed_text(text: str):
    try:
        response = client.models.embed_content(
            model=EMB_MODEL,
            contents=text
        )

        # return vector for FAISS
        return response.embeddings[0].values

    except Exception as e:
        logger.error(f"Embedding error: {str(e)}")

        # fallback vector to avoid Streamlit crash
        return [0.0] * 768


def chat(system_prompt: str, user_prompt: str):

    prompt = system_prompt + "\n\n" + user_prompt

    try:
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt
        )

        return response.text

    except Exception as e:

        logger.error(f"Gemini error: {str(e)}")

        return json.dumps({
            "score": 50,
            "substituted_ingredients": {},
            "adapted_steps": ["Error processing recipe adaptation."],
            "reason": f"API error: {str(e)}"
        })
