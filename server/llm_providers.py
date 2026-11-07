"""Unified LLM Provider Manager for Ship Court.
Manages all three active API keys:
1. Groq Cloud (gsk_...) - Primary ultra-low latency model runner (qwen/qwen3.8-27b)
2. NVIDIA NIM Primary (nvapi-ge...) - Enterprise GPU inference engine
3. NVIDIA NIM Fallback (nvapi-lg...) - Enterprise GPU secondary engine / Anthropic bridge slot
"""
import os
import json
import urllib.request
from typing import Dict, Any, Optional

class LLMProviderManager:
    def __init__(self, env_path: Optional[str] = None):
        self._load_env(env_path)
        self.groq_key = os.environ.get("GROQ_API_KEY", "")
        self.nvidia_key_1 = os.environ.get("NVIDIA_API_KEY", "")
        self.nvidia_key_2 = os.environ.get("NVIDIA_API_KEY_FALLBACK", os.environ.get("ANTHROPIC_API_KEY", ""))
        self.groq_model = os.environ.get("DEFAULT_GROQ_MODEL", "qwen/qwen3.8-27b")

    def _load_env(self, env_path: Optional[str] = None):
        if not env_path:
            possible_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
            if os.path.exists(possible_path):
                env_path = possible_path
        if env_path and os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())

    def get_keys_status(self) -> Dict[str, Any]:
        """Returns the masked status and connectivity of all three API keys."""
        def mask(k: str) -> str:
            if not k:
                return "NOT_CONFIGURED"
            if len(k) <= 12:
                return k[:3] + "..." + k[-3:]
            return k[:7] + "..." + k[-4:]

        status = {
            "key_1_groq": {
                "name": "Groq Cloud Primary",
                "env_var": "GROQ_API_KEY",
                "masked": mask(self.groq_key),
                "configured": bool(self.groq_key),
                "endpoint": "https://api.groq.com/openai/v1",
                "default_model": self.groq_model,
                "role": "Real-time Courtroom Cross-Examination Engine",
                "status": "LIVE" if self.groq_key else "INACTIVE"
            },
            "key_2_nvidia_primary": {
                "name": "NVIDIA NIM Enterprise Primary",
                "env_var": "NVIDIA_API_KEY",
                "masked": mask(self.nvidia_key_1),
                "configured": bool(self.nvidia_key_1),
                "endpoint": "https://integrate.api.nvidia.com/v1",
                "role": "Adversarial Code Forensic & Indictment Verification",
                "status": "LIVE" if self.nvidia_key_1 else "INACTIVE"
            },
            "key_3_nvidia_secondary": {
                "name": "NVIDIA NIM Secondary / Fallback",
                "env_var": "NVIDIA_API_KEY_FALLBACK / ANTHROPIC_API_KEY",
                "masked": mask(self.nvidia_key_2),
                "configured": bool(self.nvidia_key_2),
                "endpoint": "https://integrate.api.nvidia.com/v1",
                "role": "Failover Redundancy & Historical Outage Reasoner",
                "status": "LIVE" if self.nvidia_key_2 else "INACTIVE"
            }
        }
        return status

    def complete_with_groq(self, prompt: str, system_prompt: str = "You are a senior site reliability courtroom magistrate.", max_tokens: int = 150) -> Dict[str, Any]:
        """Executes real chat completion against live Groq endpoint."""
        if not self.groq_key:
            return {"error": "GROQ_API_KEY not configured"}

        url = "https://api.groq.com/openai/v1/chat/completions"
        parameters = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2
        }
        if self.groq_model.startswith('openai/gpt-oss-'):
            parameters.update(reasoning_effort='low', include_reasoning=False,
                              max_tokens=max(2048, max_tokens))
        payload = json.dumps(parameters).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json",
            "User-Agent": "ShipCourt/1.0"
        })

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                reply = data["choices"][0]["message"]["content"].strip()
                return {
                    "provider": "Groq Cloud",
                    "model": self.groq_model,
                    "status_code": resp.status,
                    "completion": reply,
                    "usage": data.get("usage", {})
                }
        except Exception as e:
            return {"error": str(e), "provider": "Groq Cloud"}
