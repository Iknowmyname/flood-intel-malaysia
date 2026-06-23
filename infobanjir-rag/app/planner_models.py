from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Operation(str, Enum):
    GET_LATEST_READING = "get_latest_reading"
    GET_LATEST_READINGS_BY_AREA = "get_latest_readings_by_area"
    GET_HIGHEST_READING = "get_highest_reading"
    GET_LOWEST_READING = "get_lowest_reading"
    GET_STATION_DETAILS = "get_station_details"
    GET_THRESHOLD_STATUS = "get_threshold_status"
    GET_RISK_FACTORS = "get_risk_factors"


OPERATION_CATALOG: dict[Operation, str] = {
    Operation.GET_LATEST_READING: (
        "Get the latest reading for one specific station."
    ),
    Operation.GET_LATEST_READINGS_BY_AREA: (
        "Get the latest readings for stations within a state or district."
    ),
    Operation.GET_HIGHEST_READING: (
        "Get the highest specified metric within a state or district."
    ),
    Operation.GET_LOWEST_READING: (
        "Get the lowest specified metric within a state or district."
    ),
    Operation.GET_STATION_DETAILS: (
        "Get station information such as its name, location, river, and status."
    ),
    Operation.GET_THRESHOLD_STATUS: (
        "Check whether rainfall or water level reached an alert, warning, "
        "or danger threshold."
    ),
    Operation.GET_RISK_FACTORS: (
        "Get the factors contributing to flood risk for a location."
    ),
}


class Location(BaseModel):
    state: str | None = Field(
        default=None,
        description="State associated with this task.",
    )
    district: str | None = Field(
        default=None,
        description="District associated with this task.",
    )
    station: str | None = Field(
        default=None,
        description="Station associated with this task.",
    )


class TimeType(str, Enum):
    CURRENT = "current"
    PAST = "past"
    RANGE = "range"
    UNSPECIFIED = "unspecified"


class Time(BaseModel):
    type: TimeType = Field(
        default=TimeType.UNSPECIFIED,
        description="Type of time constraint.",
    )
    start_time: datetime | None = Field(
        default=None,
        description="Beginning of the requested time range.",
    )
    end_time: datetime | None = Field(
        default=None,
        description="End of the requested time range.",
    )
    duration: int | None = Field(
        default=None,
        gt=0,
        description="Requested duration in hours.",
    )


class Metric(str, Enum):
    RAINFALL = "rainfall"
    WATER_LEVEL = "water_level"
    RISK = "risk_level"
    UNSPECIFIED = "unspecified"


class QueryTask(BaseModel):
    operation: Operation = Field(
        description="Data operation required for this task.",
    )
    location: Location | None = Field(
        default=None,
        description="Location associated only with this task.",
    )
    metric: Metric = Field(
        default=Metric.UNSPECIFIED,
        description="Measurement associated only with this task.",
    )
    time: Time = Field(
        default_factory=Time,
        description="Time constraint associated only with this task.",
    )


class QueryPlan(BaseModel):
    tasks: list[QueryTask] = Field(
        description="Separate data lookups required to answer the question.",
    )
    clarification: str | None = Field(
        default=None,
        description=(
            "Clarification question when required information is missing "
            "or ambiguous; otherwise null."
        ),
    )