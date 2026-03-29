import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment.")
        _client = Groq(api_key=api_key)
    return _client


def summarize_screen_text(text: str) -> str:
    try:
        client = _get_client()
        prompt = f"""You are summarizing text extracted from a user's screen.
Provide a clear concise summary in 3-5 sentences.
Focus on the main topic and key points.
Do not mention OCR or screen extraction.

Text:
{text}"""
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Summary failed: {str(e)}"

