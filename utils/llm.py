import os
import json
import time
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# GEMINI CLIENT (2.5 LITE)
# -----------------------------
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY missing")

client = genai.Client(api_key=API_KEY)

CHAT_MODEL = "gemini-3-flash-preview"


# -----------------------------
# EMBEDDING (LAZY LOAD)
# -----------------------------
embedding_model = None

def get_embedding_model():
    global embedding_model

    if embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded")
        except Exception as e:
            logger.error(f"Embedding load error: {e}")
            embedding_model = None

    return embedding_model


def embed_text(text: str):
    try:
        model = get_embedding_model()

        if model is None:
            raise ValueError("Embedding model not available")

        return model.encode(text).astype("float32").tolist()

    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return [0.0] * 384


# -----------------------------
# CHAT FUNCTION (2.5 LITE)
# -----------------------------
def chat(system_prompt: str, user_prompt: str):

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=CHAT_MODEL,
                contents=f"{system_prompt}\n\n{user_prompt}"
            )

            if hasattr(response, "text") and response.text:
                return response.text

            return json.dumps({
                "score": 50,
                "substituted_ingredients": {},
                "adapted_steps": ["Empty response"],
                "reason": "No text"
            })

        except Exception as e:
            logger.error(f"Gemini error: {e}")

            # 🔥 HANDLE QUOTA ERROR
            if "429" in str(e):
                time.sleep(40)  # wait and retry
            else:
                break

    return json.dumps({
        "score": 50,
        "substituted_ingredients": {},
        "adapted_steps": ["AI error"],
        "reason": "Retry failed"
    })