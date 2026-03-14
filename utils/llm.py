import os
import json
import time
import logging
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Models
CHAT_MODEL = "gemini-1.5-flash"
EMB_MODEL = "models/embedding-001"


# -----------------------------
# TEXT EMBEDDING FUNCTION
# -----------------------------
def embed_text(text: str):

    try:
        response = client.models.embed_content(
            model=EMB_MODEL,
            contents=[text]
        )

        # return embedding vector
        return response.embeddings[0].values

    except Exception as e:
        logger.error(f"Embedding error: {str(e)}")

        # return dummy vector so FAISS doesn't crash
        return [0.0] * 768


# -----------------------------
# GEMINI CHAT FUNCTION
# -----------------------------
def chat(system_prompt: str, user_prompt: str):

    prompt = system_prompt + "\n\n" + user_prompt

    try:

        # Rate limit protection
        time.sleep(1)

        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt
        )

        if response.text:
            return response.text

        return "{}"

    except Exception as e:

        logger.error(f"Gemini error: {str(e)}")

        # Fallback JSON
        return json.dumps({
            "score": 50,
            "substituted_ingredients": {},
            "adapted_steps": ["AI service temporarily unavailable."],
            "reason": f"Gemini API error: {str(e)}"
        })
