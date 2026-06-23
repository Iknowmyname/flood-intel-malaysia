from ..llm_models import LlmResponse, LlmPrompt
from pydantic import BaseModel
import requests


class OllamaMessage(BaseModel):
    role: str
    content: str

class OllamaJsonValidator(BaseModel):
    model: str | None = None
    message: OllamaMessage
    done: bool | None = None
    total_duration: int | None = None
    prompt_eval_count: int | None = None
    eval_count: int | None = None




class OllamaAdapter():

    def __init__(self, base_url, model, timeout, keep_alive, retries):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.keep_alive = keep_alive
        self.retries = retries


    def generate(self, prompt: LlmPrompt, json_mode: bool = False) -> LlmResponse:


        payload = {
            "model": self.model,
            "stream": False,
            "keep_alive": self.keep_alive,
            "messages": [
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt}
            ]

        }

        if json_mode:
            payload["format"] = "json"

        for attempt in range(1, self.retries + 2):
            
            try:
                response = requests.post(
                    url=f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout
                )

                response.raise_for_status()
                data = response.json()

                validated_data = OllamaJsonValidator.model_validate(data)

                return LlmResponse(
                    response=validated_data.message.content.strip(),
                    input_tokens=validated_data.prompt_eval_count,
                    output_tokens=validated_data.eval_count,
                    provider_name="ollama",
                    llm_model=validated_data.model or self.model,
                    response_latency=(
                        validated_data.total_duration / 1_000_000
                        if validated_data.total_duration is not None
                        else None
                    ),
                )

            except requests.HTTPError as http_error:
            
                response = http_error.response

                if response is None:
                    raise

                status_code = response.status_code if response.status_code is not None else None
            

                if status_code >= 500 or status_code == 429:
                    if attempt <= self.retries:
                        continue
                    raise
                else:
                    raise
                
            
            except (requests.Timeout, requests.ConnectionError):
                if attempt <= self.retries:
                    continue
                raise
    
    
    def check_ollama_health(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return True
        except Exception:
            return False
