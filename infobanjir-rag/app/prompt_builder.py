import json
from datetime import datetime, timezone

from .llm_models import LlmPrompt
from .planner_models import OPERATION_CATALOG, QueryPlan

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



def build_operation_section() -> str:

    operation_list = []
    
    for operation, description in OPERATION_CATALOG.items():
        operation_list.append(f"Operation : {operation}, Description : {description}")

    return "\n".join(operation_list)




def build_plan_prompt(question: str) -> LlmPrompt:
    today = datetime.now(timezone.utc).date().isoformat()

    # Compact serialization reduces prompt tokens.
    schema = json.dumps(
        QueryPlan.model_json_schema(),
        separators=(",", ":"),
    )

    system_prompt = f"""
        You are a query planner for a Malaysian flood-information system.
        Do not answer the user's question.
        Return only valid JSON matching the provided schema.

        Today: {today}

        Allowed operations:
        {build_operation_section()}

        Rules:
        - Create one task for each separate data lookup.
        - Keep every operation with its own location, metric, time.
        - Never mix fields belonging to different parts of the question.
        - Use get_latest_reading when one specific station's reading is requested.
        - Use highest or lowest operations only across a state or district.
        - Use null when an optional value was not provided.
        - Do not invent locations, stations, metrics, dates, or operations.
        - The tasks only specify required data; do not create a comparison task.
        - If required information is missing or ambiguous, provide clarification.
        - Return no Markdown, commentary, or fields outside the schema.

        JSON schema:
        {schema}
        """.strip()

    return LlmPrompt(
        system_prompt=system_prompt,
        user_prompt=question.strip(),
    )