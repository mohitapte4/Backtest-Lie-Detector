"""
Model client wrappers for LLM API calls.

Provides a unified interface for calling OpenAI and Anthropic models,
with support for JSON extraction and retry logic.
"""

import json
import os
import re
import time
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from backtest_lie_detector.schemas import ModelResponse, Validity, ViolationType

load_dotenv()


class BaseModelClient(ABC):
    """Abstract base class for model clients."""
    
    @abstractmethod
    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> tuple[str, float]:
        """
        Call the model with the given prompts.
        
        Args:
            system_prompt: The system/instruction prompt.
            user_prompt: The user's query.
            temperature: Sampling temperature (0.0 for deterministic).
            max_tokens: Maximum tokens in the response.
        
        Returns:
            Tuple of (response_text, latency_ms).
        """
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        pass


class OpenAIClient(BaseModelClient):
    """Client wrapper for OpenAI API."""
    
    def __init__(self, model: str = "gpt-4o"):
        """
        Initialize the OpenAI client.
        
        Args:
            model: Model identifier (e.g., "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo").
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self._model = model
        self._client = OpenAI(api_key=api_key)
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> tuple[str, float]:
        """Call OpenAI API and return response with latency."""
        start_time = time.time()
        
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        response_text = response.choices[0].message.content or ""
        
        return response_text, latency_ms


class AnthropicClient(BaseModelClient):
    """Client wrapper for Anthropic API."""
    
    def __init__(self, model: str = "claude-sonnet-4-5"):
        """
        Initialize the Anthropic client.
        
        Args:
            model: Model identifier (e.g., "claude-sonnet-4-5", "claude-opus-4-5").
        """
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")
        
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        
        self._model = model
        self._client = anthropic.Anthropic(api_key=api_key)
    
    @property
    def model_name(self) -> str:
        return self._model
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> tuple[str, float]:
        """Call Anthropic API and return response with latency."""
        start_time = time.time()
        
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        response_text = response.content[0].text if response.content else ""
        
        return response_text, latency_ms


def get_client(provider: str, model: str) -> BaseModelClient:
    """
    Factory function to get the appropriate model client.
    
    Args:
        provider: API provider ("openai" or "anthropic").
        model: Model identifier.
    
    Returns:
        Configured model client.
    
    Raises:
        ValueError: If provider is not supported.
    """
    provider = provider.lower()
    
    if provider == "openai":
        return OpenAIClient(model=model)
    elif provider == "anthropic":
        return AnthropicClient(model=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}. Use 'openai' or 'anthropic'.")


def extract_json_from_text(text: str) -> str:
    """
    Extract JSON object from text that may contain additional content.
    
    Handles cases where the model includes markdown code blocks or
    explanatory text around the JSON.
    
    Args:
        text: Raw text potentially containing JSON.
    
    Returns:
        Extracted JSON string, or empty string if not found.
    """
    text = text.strip()
    
    # Try to find JSON in markdown code block
    code_block_pattern = r"```(?:json)?\s*(\{[\s\S]*?\})\s*```"
    match = re.search(code_block_pattern, text)
    if match:
        return match.group(1).strip()
    
    # Try to find a JSON object directly
    # Look for outermost { } pair
    first_brace = text.find("{")
    if first_brace == -1:
        return ""
    
    # Find matching closing brace
    depth = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text[first_brace:], start=first_brace):
        if escape_next:
            escape_next = False
            continue
        
        if char == "\\":
            escape_next = True
            continue
        
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[first_brace:i + 1]
    
    # If no matching brace found, return from first brace to end
    return text[first_brace:]


def parse_model_json(raw_text: str) -> Optional[ModelResponse]:
    """
    Parse model response text into a ModelResponse object.
    
    Handles various formatting issues and attempts to extract
    valid JSON from the response.
    
    Args:
        raw_text: Raw text response from the model.
    
    Returns:
        Parsed ModelResponse, or None if parsing fails.
    """
    if not raw_text:
        return None
    
    # Extract JSON from the response
    json_str = extract_json_from_text(raw_text)
    if not json_str:
        return None
    
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Try to fix common JSON issues
        json_str = json_str.replace("'", '"')  # Single to double quotes
        json_str = re.sub(r",\s*}", "}", json_str)  # Trailing commas
        json_str = re.sub(r",\s*]", "]", json_str)  # Trailing commas in arrays
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    if not isinstance(data, dict):
        return None
    
    # Normalize field names (handle case variations)
    normalized = {}
    for key, value in data.items():
        normalized[key.lower()] = value
    
    # Extract and validate required fields
    try:
        validity_str = normalized.get("validity", "invalid")
        if isinstance(validity_str, str):
            validity_str = validity_str.lower()
            if validity_str not in ["valid", "invalid", "ambiguous"]:
                validity_str = "invalid"  # Default to invalid if unclear
        validity = Validity(validity_str)
        
        # Parse violations
        violations_raw = normalized.get("violations", [])
        violations = []
        if isinstance(violations_raw, list):
            for v in violations_raw:
                if isinstance(v, str):
                    try:
                        violations.append(ViolationType(v))
                    except ValueError:
                        # Skip unrecognized violation types
                        continue
        
        # Get other fields with defaults
        explanation = str(normalized.get("explanation", ""))
        
        repair_raw = normalized.get("repair", [])
        repair = []
        if isinstance(repair_raw, list):
            repair = [str(r) for r in repair_raw]
        elif isinstance(repair_raw, str):
            repair = [repair_raw]
        
        confidence = float(normalized.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
        
        return ModelResponse(
            validity=validity,
            violations=violations,
            explanation=explanation,
            repair=repair,
            confidence=confidence,
        )
    
    except Exception:
        return None


class MockClient(BaseModelClient):
    """
    Mock client for testing without API calls.
    
    Returns predefined responses based on simple pattern matching.
    """
    
    def __init__(self, model: str = "mock-model"):
        self._model = model
    
    @property
    def model_name(self) -> str:
        return self._model
    
    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2000,
    ) -> tuple[str, float]:
        """Return a mock response based on simple keyword matching."""
        # Simulate some latency
        time.sleep(0.1)
        
        prompt_lower = user_prompt.lower()
        
        # Default response
        response = {
            "validity": "invalid",
            "violations": ["survivorship_bias"],
            "explanation": "This is a mock response for testing.",
            "repair": ["This is a mock repair suggestion."],
            "confidence": 0.75
        }
        
        # Customize based on keywords
        if "meta" in prompt_lower and "2018" in prompt_lower:
            response = {
                "validity": "invalid",
                "violations": ["identifier_time_travel"],
                "explanation": "META ticker did not exist in 2018.",
                "repair": ["Use FB ticker for pre-2022 periods."],
                "confidence": 0.90
            }
        elif "filing" in prompt_lower and ("4:07" in prompt_lower or "after" in prompt_lower):
            response = {
                "validity": "invalid",
                "violations": ["filing_clock_leakage"],
                "explanation": "Filing was not available at decision time.",
                "repair": ["Trade after filing is available."],
                "confidence": 0.85
            }
        elif "still listed" in prompt_lower or "current" in prompt_lower:
            response = {
                "validity": "invalid",
                "violations": ["survivorship_bias", "delisting_return_omission"],
                "explanation": "Using current universe introduces survivorship bias.",
                "repair": ["Use point-in-time universe.", "Include delisting returns."],
                "confidence": 0.88
            }
        
        return json.dumps(response), 100.0  # 100ms mock latency
