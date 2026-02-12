"""
Unified LLM Interface Manager

Supports both local Ollama and cloud LLM API with easy switching.
Provides a unified interface for querying different LLM backends.

Example:
    # Local mode (free, requires Ollama running)
    llm = create_local_llm()
    response = llm.query("What is NDVI?", system_prompt="Answer in one sentence.")

    # Cloud mode (paid API)
    llm = create_cloud_llm()
    response = llm.query("What is NDVI?")

    # Switch modes dynamically
    llm.switch_mode("cloud")
"""

import os
import json
import requests
from typing import Optional, Literal
from dotenv import load_dotenv

load_dotenv()


class LLMManager:
    """Unified LLM interface supporting local Ollama and cloud LLM API."""

    def __init__(
        self,
        mode: Literal["local", "cloud"] = "local",
        local_model: str = "llama3.2:latest",
        cloud_api_key: Optional[str] = None
    ):
        """
        Initialize LLM Manager.

        Args:
            mode: "local" for Ollama or "cloud" for Cloud LLM API
            local_model: Ollama model name (default: llama3.2:latest)
            cloud_api_key: Cloud LLM API key (uses env var if not provided)

        Example:
            llm = LLMManager(mode="local", local_model="llama3.2:3b")
            llm = LLMManager(mode="cloud", cloud_api_key="sk-...")
        """
        self.mode = mode
        self.local_model = local_model
        self.local_url = "http://localhost:11434/api/generate"
        self.cloud_url = "https://api.anthropic.com/v1/messages"
        self.cloud_model = "claude-3-5-sonnet-20241022"

        # Get Cloud LLM API key
        self.cloud_api_key = cloud_api_key or os.getenv("CLOUD_LLM_API_KEY")

        if self.mode == "local":
            print(f"🤖 LLM Manager initialized in LOCAL mode")
            print(f"   Using Ollama model: {self.local_model}")
        else:
            if self.cloud_api_key:
                print(f"🤖 LLM Manager initialized in CLOUD mode")
                print(f"   Using Cloud LLM API")
            else:
                print(f"⚠️ CLOUD mode selected but CLOUD_LLM_API_KEY not found")
                print(f"   Set CLOUD_LLM_API_KEY environment variable or pass cloud_api_key param")

    def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500
    ) -> str:
        """
        Query the LLM.

        Args:
            prompt: Main prompt/question
            system_prompt: Optional system message to guide behavior
            temperature: Temperature for response (0.0-1.0, lower=more focused)
            max_tokens: Maximum tokens in response

        Returns:
            LLM response string

        Example:
            response = llm.query(
                "What irrigation frequency for Jowar?",
                system_prompt="You are a farming expert.",
                temperature=0.3
            )
        """
        if self.mode == "local":
            return self._query_local(prompt, system_prompt, temperature, max_tokens)
        elif self.mode == "cloud":
            return self._query_cloud(prompt, system_prompt, temperature, max_tokens)
        else:
            return "❌ ERROR: Invalid mode"

    def _query_local(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Query local Ollama instance."""
        try:
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt

            payload = {
                "model": self.local_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature
                }
            }

            response = requests.post(
                self.local_url,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                return f"❌ ERROR: Ollama returned status {response.status_code}"

        except requests.exceptions.ConnectionError:
            return "❌ ERROR: Cannot connect to Ollama. Make sure 'ollama serve' is running on localhost:11434"
        except requests.exceptions.Timeout:
            return "❌ ERROR: Ollama query timed out (30s)"
        except Exception as e:
            return f"❌ ERROR: Local query failed - {str(e)}"

    def _query_cloud(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Query Cloud LLM API."""
        try:
            if not self.cloud_api_key:
                return "❌ ERROR: CLOUD_LLM_API_KEY not set. Set environment variable or pass cloud_api_key to constructor"

            headers = {
                "x-api-key": self.cloud_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }

            messages = [
                {"role": "user", "content": prompt}
            ]

            system_msg = system_prompt or ""

            payload = {
                "model": self.cloud_model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_msg,
                "messages": messages
            }

            response = requests.post(
                self.cloud_url,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result["content"][0]["text"].strip()
            elif response.status_code == 401:
                return "❌ ERROR: Invalid Cloud LLM API key. Check CLOUD_LLM_API_KEY"
            elif response.status_code == 429:
                return "❌ ERROR: Cloud LLM API rate limit exceeded. Try again later"
            else:
                return f"❌ ERROR: Cloud LLM API returned status {response.status_code}"

        except requests.exceptions.Timeout:
            return "❌ ERROR: Cloud LLM API query timed out (30s)"
        except Exception as e:
            return f"❌ ERROR: Cloud query failed - {str(e)}"

    def switch_mode(self, new_mode: Literal["local", "cloud"]) -> str:
        """
        Switch between local and cloud modes.

        Args:
            new_mode: "local" or "cloud"

        Returns:
            Status message
        """
        if new_mode not in ["local", "cloud"]:
            return f"❌ ERROR: Invalid mode '{new_mode}'. Use 'local' or 'cloud'"

        self.mode = new_mode

        if new_mode == "local":
            print(f"🔄 Switched to LOCAL mode")
            print(f"   Using Ollama model: {self.local_model}")
            return f"🔄 Switched to LOCAL mode"
        else:
            if self.cloud_api_key:
                print(f"🔄 Switched to CLOUD mode")
                print(f"   Using Cloud LLM API")
                return f"🔄 Switched to CLOUD mode"
            else:
                print(f"⚠️ CLOUD mode selected but API key not available")
                return f"⚠️ CLOUD mode selected but CLOUD_LLM_API_KEY not set"


def create_local_llm(model: str = "llama3.2:latest") -> LLMManager:
    """
    Create LLM Manager in local mode (free, requires Ollama).

    Args:
        model: Ollama model name (default: llama3.2:latest)

    Returns:
        LLMManager configured for local Ollama
    """
    return LLMManager(mode="local", local_model=model)


def create_cloud_llm(api_key: Optional[str] = None) -> LLMManager:
    """
    Create LLM Manager in cloud mode (paid Cloud LLM API).

    Args:
        api_key: Cloud LLM API key (uses CLOUD_LLM_API_KEY env var if not provided)

    Returns:
        LLMManager configured for Cloud LLM API
    """
    return LLMManager(mode="cloud", cloud_api_key=api_key)
