from datetime import datetime, timezone
from .llm_models import LlmPrompt


SYSTEM_PROMPT = (
    "You are a helpful flood intelligence assistant.\n"
    "Answer the question using only the context.\n"
    "If the context is insufficient, say that clearly.\n"
)

def build_prompt(question: str, context: str) -> LlmPrompt:

    today = datetime.now(timezone.utc).date().isoformat()

    return LlmPrompt(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"Today: {today}\n\nContext: {context}\n\n Question: {question}"
    )