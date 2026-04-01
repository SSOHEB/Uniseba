import os
import json
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


def build_knowledge_graph(text, target_word):
    try:
        client = _get_client()
        trimmed_text = (text or "")[:4000]
        focus = (target_word or "").strip()
        prompt = f"""Extract a knowledge graph centered on "{focus}" from the text below.

Requirements:
- Create 8 to 15 nodes representing key concepts, people, places, events, or ideas from the text.
- One node must be "{focus}" as the central node.
- Create edges between nodes with short relationship labels (2 to 4 words max).
- Only include relationships clearly supported by the text.
- Return ONLY valid JSON with no explanation, no markdown, no backticks.
- JSON format must be exactly:
{{"nodes": [{{"id": "1", "label": "..."}}], "edges": [{{"from": "1", "to": "2", "label": "..."}}]}}

Text:
{trimmed_text}"""
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
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        return f"Graph failed: {str(e)}"
