"""Serializers to map field names between Convex (camelCase) and FastAPI (snake_case).

Mapping table:
_id -> id
_creationTime -> created_at
firstName -> first_name
lastName -> last_name
employeeId -> employee_id
checkIn -> check_in
checkOut -> check_out
workHours -> work_hours
leaveType -> leave_type
"""
from typing import Any, Dict

CONVEX_TO_FASTAPI = {
    "_id": "id",
    "_creationTime": "created_at",
    "firstName": "first_name",
    "lastName": "last_name",
    "employeeId": "employee_id",
    "checkIn": "check_in",
    "checkOut": "check_out",
    "workHours": "work_hours",
    "leaveType": "leave_type",
}

FASTAPI_TO_CONVEX = {v: k for k, v in CONVEX_TO_FASTAPI.items()}


def map_keys(obj: Dict[str, Any], key_map: Dict[str, str]) -> Dict[str, Any]:
    """Shallow map of dictionary keys according to key_map. Unknown keys are kept as-is."""
    if obj is None:
        return obj
    out: Dict[str, Any] = {}
    for k, v in obj.items():
        out_key = key_map.get(k, k)
        out[out_key] = v
    return out


def convex_to_fastapi(data: Any) -> Any:
    """Convert Convex-style (camelCase) dict keys to FastAPI-style (snake_case).

    Works shallowly and preserves non-dict values. If a list is provided,
    it will map each element if the element is a dict.
    """
    if isinstance(data, list):
        return [convex_to_fastapi(d) for d in data]
    if not isinstance(data, dict):
        return data
    return map_keys(data, CONVEX_TO_FASTAPI)


def fastapi_to_convex(data: Any) -> Any:
    """Convert FastAPI-style (snake_case) dict keys to Convex-style (camelCase).

    Works shallowly and preserves non-dict values. If a list is provided,
    it will map each element if the element is a dict.
    """
    if isinstance(data, list):
        return [fastapi_to_convex(d) for d in data]
    if not isinstance(data, dict):
        return data
    return map_keys(data, FASTAPI_TO_CONVEX)


__all__ = [
    "convex_to_fastapi",
    "fastapi_to_convex",
    "CONVEX_TO_FASTAPI",
    "FASTAPI_TO_CONVEX",
]
