from pydantic import BaseModel
from enum import Enum

class Intent(str, Enum):
    LATEST_READING = "latest_reading"
    CURRENT_STATUS = "current_status"
    RANKING= "ranking"
    COMPARISON = "comparison"
    STATE_SUMMARY = "state_summary"
    DISTRICT_SUMMARY = "district_summary"
    STATION_LOOKUP = "station_lookup"
    RISK_EXPLANATION = "risk_explanation"


class Operation(str, Enum):
    GET_LATEST_READING = "GET_LATEST_READING"
    GET_STATION_DETAILS = "GET_STATION_DETAILS"
    GET_STATIONS_BY_LOCATION = "GET_STATIONS_BY_LOCATION"
    GET_LATEST_READINGS_BY_DISTRICT = "GET_LATEST_READINGS_BY_DISTRICT"
    GET_LATEST_READINGS_BY_STATE = "GET_LATEST_READINGS_BY_STATE"
    GET_THRESHOLD_STATUS = "GET_THRESHOLD_STATUS"
    GET_RANKED_STATIONS = "GET_RANKED_STATIONS"
    GET_RANKED_DISTRICTS = "GET_RANKED_DISTRICTS"
    COMPARE_LOCATIONS = "COMPARE_LOCATIONS"
    GET_RISK_FACTORS = "GET_RISK_FACTORS"



class IntentDefinition(BaseModel):
    intent: Intent
    description: str
    operation: list[Operation]
    

INTENT_CATALOG = {
    Intent.LATEST_READING: IntentDefinition(
        description="User asks for the latest rainfall or water level reading.",
        operations=[Operation.GET_LATEST_READING],
        requires_location=True,
        default_answer_mode="template"
    ),

    Intent.DISTRICT_SUMMARY: IntentDefinition(
        description="User asks for a current summary of flood readings in a district.",
        operations=[Operation.GET_LATEST_READINGS_BY_DISTRICT],
        requires_location=True,
        default_answer_mode="llm_with_context"
    ),

    Intent.STATE_SUMMARY: IntentDefinition(
        description="User asks for a current summary of flood readings in a state.",
        operations=[Operation.GET_LATEST_READINGS_BY_STATE],
        requires_location=True,
        default_answer_mode="llm_with_context"
    ),

    Intent.RANKING: IntentDefinition(
        description="User asks for highest, lowest, most risky, or top stations/districts/states.",
        operations=[Operation.GET_RANKED_STATIONS],
        requires_location=False,
        default_answer_mode="template"
    ),

    Intent.COMPARISON: IntentDefinition(
        description="User asks to compare flood readings between locations, stations, or metrics.",
        operations=[Operation.COMPARE_LOCATIONS],
        requires_location=True,
        default_answer_mode="llm_with_context"
    ),

    Intent.RISK_EXPLANATION: IntentDefinition(
        description="User asks why a location or station is risky.",
        operations=[Operation.GET_RISK_FACTORS],
        requires_location=True,
        default_answer_mode="llm_with_context"
    ),
}