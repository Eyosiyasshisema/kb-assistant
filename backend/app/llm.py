import time
from pathlib import Path
from google import genai
from google.genai import errors, types
from pydantic import BaseModel
from .config import settings

client = genai.Client(api_key=settings.gemini_api_key)
PROMPT_DIR = Path(__file__).parent / "prompts"

class Submission(BaseModel):
    answerable: bool
    answer: str
    citations: list[int]
    confidence: float

def load_prompt(version: str) -> str:
    return (PROMPT_DIR / f"{version}.txt").read_text(encoding="utf-8")

def ask_llm(system: str, context: str, question: str):
    """Returns (Submission | None, usage). Retries on rate limits and malformed output."""
    usage = {"in": 0, "out": 0}
    user = f"<context>\n{context}\n</context>\n\nQuestion: {question}"
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model=settings.llm_model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=Submission,
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )
            um = resp.usage_metadata
            if um:
                usage["in"] += um.prompt_token_count or 0
                usage["out"] += um.candidates_token_count or 0
            sub = resp.parsed
            if isinstance(sub, Submission) and 0 <= sub.confidence <= 1:
                return sub, usage
        except errors.APIError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            break
        except Exception:
            continue
    return None, usage