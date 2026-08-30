import asyncio
import json
import os

from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI

from ai.prompts.reasoning import REASONING_PROMPT_TEMPLATE, ExplanationResult


class LLMExplanationError(Exception):
    pass

async def generate_explanation(
    amount_paise: int,
    failure_type: str,
    recoverability_score: float,
    risk_level: str,
    action_type: str,
    authorization_status: str,
    reason: str,
    timeout_seconds: float = 30.0
) -> ExplanationResult:
    """
    Generates a human-readable explanation and reason codes using an LLM.
    Implements a circuit breaker (timeout) and a fallback to OpenAI if Gemini fails.
    Returns the parsed ExplanationResult.
    """
    from config import settings
    if settings.llm_provider == "mock":
        return ExplanationResult(
            narrative="due to Low risk score.",
            reason_codes=["MOCKED_REASON"]
        )

    prompt = REASONING_PROMPT_TEMPLATE.format(
        amount_paise=amount_paise,
        failure_type=failure_type,
        recoverability_score=recoverability_score,
        risk_level=risk_level,
        action_type=action_type,
        authorization_status=authorization_status,
        reason=reason or "N/A"
    )

    try:
        # Wrap the entire LLM chain in a timeout
        return await asyncio.wait_for(
            _call_llms(prompt),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        raise LLMExplanationError("LLM API call timed out.")
    except Exception as e:
        raise LLMExplanationError(f"LLM API call failed: {e!s}")

async def _call_llms(prompt: str) -> ExplanationResult:
    """Calls Gemini first, falls back to OpenAI."""
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    
    last_error = None
    
    if gemini_key:
        try:
            return await _call_gemini(prompt, gemini_key)
        except Exception as e:
            last_error = e
            
    if openai_key:
        try:
            return await _call_openai(prompt, openai_key)
        except Exception as e:
            last_error = e
            
    raise last_error or RuntimeError("No LLM API keys configured.")

async def _call_gemini(prompt: str, api_key: str) -> ExplanationResult:
    client = genai.Client(api_key=api_key)
    # google-genai client is synchronous by default unless we use asyncio executor or the async client
    # Assuming google.genai has async support or we run in executor. The standard `client.models.generate_content` is sync.
    # To avoid blocking the event loop, we use asyncio.to_thread
    response = await asyncio.to_thread(
        client.models.generate_content,
        model='gemini-3.6-flash',
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExplanationResult,
        )
    )
    # Parse the validated text
    data = json.loads(response.text)
    return ExplanationResult(**data)

async def _call_openai(prompt: str, api_key: str) -> ExplanationResult:
    client = AsyncOpenAI(api_key=api_key)
    response = await client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful AI explaining decisions."},
            {"role": "user", "content": prompt}
        ],
        response_format=ExplanationResult,
    )
    return response.choices[0].message.parsed
