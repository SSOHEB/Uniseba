"""Groq LLM client for Uniseba"""

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
