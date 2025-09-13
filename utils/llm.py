import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import logging
from google.api_core import exceptions
from google.api_core import retry

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHAT_MODEL = "gemini-2.5-flash"
EMB_MODEL = "models/text-embedding-004"

# Retry settings with increased timeout and exponential backoff
@retry.Retry(
    predicate=retry.if_transient_error,
    initial_delay=1.0,
    maximum_delay=10.0,
    timeout=120.0  # Increased from 60.0s to 120.0s
)
def embed_text(text: str):
    try:
        resp = genai.embed_content(model=EMB_MODEL, content=text)
        return resp["embedding"]
    except exceptions.ServiceUnavailable as e:
        logger.error(f"Service unavailable error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error in embedding: {str(e)}")
        raise

@retry.Retry(
    predicate=retry.if_transient_error,
    initial_delay=1.0,
    maximum_delay=10.0,
    timeout=120.0
)
def chat(system_prompt: str, user_prompt: str):
    model = genai.GenerativeModel(CHAT_MODEL)
    prompt = system_prompt + "\n\n" + user_prompt

    try:
        resp = model.generate_content(
            [{"role": "user", "parts": prompt}],
            generation_config={"response_mime_type": "application/json"}
        )
        text = resp.text.strip()
        return text
    except Exception as e:
        logger.error(f"Error in Gemini API call: {str(e)}")
        return json.dumps({
            "score": 50,
            "substituted_ingredients": {},
            "adapted_steps": ["Error processing recipe adaptation."],
            "reason": f"API error: {str(e)}"
        })