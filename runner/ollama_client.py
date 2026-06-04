import json
import requests


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def _request(self, method: str, path: str, json_data: dict | None = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        resp = requests.request(method, url, json=json_data, timeout=120)
        resp.raise_for_status()
        return resp

    def chat(self, messages: list[dict], temperature: float = 0.7, response_format: str | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if response_format == "json":
            payload["format"] = "json"
        resp = self._request("POST", "/api/chat", payload)
        data = resp.json()
        return data["message"]["content"]

    def ping(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False
