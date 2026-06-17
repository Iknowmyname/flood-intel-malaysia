from pydantic import BaseModel


class LlmResponse(BaseModel):

    response: str
    input_tokens: int | None
    output_tokens: int | None
    provider_name: str
    llm_model: str
    response_latency: float | None


class LlmPrompt(BaseModel):
    system_prompt: str
    user_prompt: str
