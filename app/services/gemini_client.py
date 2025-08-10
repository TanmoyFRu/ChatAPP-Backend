import logging
import httpx
from typing import List, Dict, Optional
from app.core.config import settings
import json

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

class GeminiClient:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")
        self.api_url = f"{GEMINI_API_URL}?key={settings.GEMINI_API_KEY}"

    async def generate_response(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Sends a prompt to Gemini and returns the AI's text response.
        """
        try:
            # Build prompt with optional history
            if conversation_history:
                context = "Previous conversation:\n"
                for msg in conversation_history[-5:]:
                    username = msg.get("username", "User")
                    context += f"{username}: {msg['content']}\n"
                context += f"\nUser: {message}\nAI:"
            else:
                context = f"User: {message}\nAI:"

            payload = {
                "prompt": {
                    "text": context
                },
                "temperature": 0.2,
                "maxOutputTokens": 512
            }

            logger.debug(f"Sending request to Gemini API: {json.dumps(payload)}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                resp.raise_for_status()
                data = resp.json()

            logger.debug(f"Received Gemini API response: {json.dumps(data)}")

            # Extract content
            for list_key in ("candidates", "outputs", "output"):
                lst = data.get(list_key)
                if isinstance(lst, list) and lst:
                    first = lst[0]
                    if isinstance(first, dict):
                        content = first.get("content") or first.get("text") or first.get("output")
                        if content:
                            return content
                    else:
                        return str(first)

            for key in ("content", "generated_text", "response", "text"):
                if key in data:
                    return data[key]

            def find_first_string(v):
                if isinstance(v, str):
                    return v
                if isinstance(v, dict):
                    for vv in v.values():
                        res = find_first_string(vv)
                        if res:
                            return res
                if isinstance(v, list):
                    for item in v:
                        res = find_first_string(item)
                        if res:
                            return res
                return None

            nested = find_first_string(data)
            if nested:
                return nested

            return "Sorry, I could not generate a reply."

        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API HTTP error {e.response.status_code}: {e.response.text}")
            return "Sorry, the AI service returned an error."
        except Exception as e:
            logger.error(f"Unexpected error during Gemini API call: {e}")
            return "I'm experiencing technical difficulties. Please try again later."

# Single shared instance
gemini_client = GeminiClient()
