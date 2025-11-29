"""
llm client for ollama integration
handles all communication with the local ollama qwen3:4b model
"""
import json
import requests
from typing import Dict, Any, Optional


class OllamaClient:
    """client for interacting with local ollama instance"""
    
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config['llm']['base_url']
        self.model = config['llm']['model']
        self.temperature = config['llm'].get('temperature', 0.7)
        self.max_tokens = config['llm'].get('max_tokens', 2000)
        
    def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False
    ) -> str:
        """
        generate completion from ollama
        
        args:
            prompt: user prompt
            system_prompt: system instructions
            temperature: override default temperature
            json_mode: force json output format
            
        returns:
            generated text response
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature or self.temperature,
            "stream": False,
            "options": {
                "num_predict": self.max_tokens
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        if json_mode:
            payload["format"] = "json"
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
            
        except requests.exceptions.Timeout:
            raise Exception(f"Ollama request timed out for model {self.model}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama request failed: {str(e)}")
    
    def generate_json(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        generate json response from ollama
        
        args:
            prompt: user prompt
            system_prompt: system instructions
            temperature: override default temperature
            
        returns:
            parsed json dictionary
        """
        response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            json_mode=True
        )
        
        try:
            # try to parse the response as json
            return json.loads(response)
        except json.JSONDecodeError:
            # if it fails, try to extract json from markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
            else:
                raise Exception(f"Failed to parse JSON from response: {response[:200]}")
    
    def health_check(self) -> bool:
        """check if ollama is running and model is available"""
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            return self.model in model_names
        except:
            return False