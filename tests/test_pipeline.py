import pandas as pd
from src.pipeline import apply_delta, build_report

def test_apply_delta_handles_add_update_delete():
    state = pd.DataFrame({"id": ["1", "2"], "value": ["a", "b"]})
    delta = pd.DataFrame([
        {"id": "3", "value": "c", "action": "add"},
        {"id": "2", "value": "updated", "action": "update"},
        {"id": "1", "value": None, "action": "delete"},
    ])
    result = apply_delta(state, delta, "id").sort_values("id").reset_index(drop=True)
    assert result.to_dict("records") == [
        {"id": "2", "value": "updated"}, {"id": "3", "value": "c"}
    ]

def test_deleted_category_becomes_unknown():
    states = {
        "interactions": pd.DataFrame([{
            "interaction_id": "I1", "interaction_start": "2025-01-10T12:00:00Z",
            "channel": "phone", "category_id": "DELETED", "contact_center_id": "CC1",
            "call_duration_minutes": 10
        }]),
        "contact_centers": pd.DataFrame([{"contact_center_id": "CC1", "contact_center_name": "Center 1"}]),
        "service_categories": pd.DataFrame([{"category_id": "OTHER", "department": "IT"}]),
    }
    assert build_report(states).loc[0, "department"] == "Unknown"

def test_month_uses_interaction_start_not_delta_timestamp():
    states = {
        "interactions": pd.DataFrame([{
            "interaction_id": "I1", "timestamp": "2025-03-15T12:00:00Z",
            "interaction_start": "2025-01-10T12:00:00Z", "channel": "phone",
            "category_id": "CAT", "contact_center_id": "CC1", "call_duration_minutes": 10
        }]),
        "contact_centers": pd.DataFrame([{"contact_center_id": "CC1", "contact_center_name": "Center 1"}]),
        "service_categories": pd.DataFrame([{"category_id": "CAT", "department": "IT"}]),
    }
    assert build_report(states).loc[0, "month"] == "2025-01"
