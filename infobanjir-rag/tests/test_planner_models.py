import pytest
from pydantic import ValidationError

from app.planner_models import Metric, Operation, QueryPlan, TimeType


def test_query_plan_validates_supported_values():
    plan = QueryPlan.model_validate(
        {
            "tasks": [
                {
                    "operation": "get_highest_reading",
                    "location": {"state": "Selangor"},
                    "metric": "rainfall",
                    "time": {"type": "current"},
                }
            ],
            "clarification": None,
        }
    )

    task = plan.tasks[0]
    assert task.operation is Operation.GET_HIGHEST_READING
    assert task.location.state == "Selangor"
    assert task.metric is Metric.RAINFALL
    assert task.time.type is TimeType.CURRENT


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("operation", "delete_all_readings"),
        ("metric", "temperature"),
    ],
)
def test_query_plan_rejects_unsupported_options(field, value):
    task = {
        "operation": "get_latest_reading",
        "location": {"station": "Station ABC"},
        "metric": "rainfall",
        "time": {"type": "current"},
    }
    task[field] = value

    with pytest.raises(ValidationError):
        QueryPlan.model_validate({"tasks": [task]})


def test_query_plan_requires_tasks_field():
    with pytest.raises(ValidationError):
        QueryPlan.model_validate({"clarification": "Which station?"})


def test_query_task_applies_time_and_metric_defaults():
    plan = QueryPlan.model_validate(
        {
            "tasks": [
                {
                    "operation": "get_station_details",
                    "location": {"station": "Station ABC"},
                }
            ]
        }
    )

    task = plan.tasks[0]
    assert task.metric is Metric.UNSPECIFIED
    assert task.time.type is TimeType.UNSPECIFIED
