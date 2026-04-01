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
        client = _get_client().with_options(timeout=25)
        words = str(text or "").split()
        filtered_words = []
        for word in words:
            token = word.strip(".,;:!?()[]{}\"'")
            if len(token) <= 4 and token.isupper():
                continue
            filtered_words.append(word)
        cleaned_text = " ".join(filtered_words)
        prompt = f"""You are a knowledge graph builder analyzing a study or learning document.

Extract a knowledge graph from the text below.

Rules:
- Create 10 to 15 nodes representing key concepts, skills, topics or ideas.
- Automatically identify the most important concept as the central node.
- Create meaningful edges between related nodes.
- Each edge label must be specific and descriptive: use labels like
  "builds on", "required for", "teaches", "leads to", "includes",
  "depends on", "stronger than", "used in", "part of mastering".
- Never use the same edge label more than twice across all edges.
- Never use generic labels like "part of" or "related to" alone.
- The central node must be a meaningful topic or skill, never a
  status word or common short word.
- Return ONLY valid JSON with no explanation, no markdown, no backticks.
- JSON format must be exactly:
  {{"center": "central node label", "nodes": [{{"id": "1", "label": "..."}}], "edges": [{{"from": "1", "to": "2", "label": "..."}}]}}

Text:
{cleaned_text[:6000]}"""
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
