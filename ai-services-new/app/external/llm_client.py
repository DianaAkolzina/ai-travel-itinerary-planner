import requests
from app.config import settings

class LLMClient:
    """Client for LLM API services"""
    
    def __init__(self):
        self.endpoint = settings.llm_endpoint
        self.model = settings.llm_model
    
    async def generate(self, prompt: str) -> dict:
        """Send request to LLM API"""
        try:
            response = requests.post(self.endpoint, json={
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"LLM API returned status {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"LLM connection failed: {e}")