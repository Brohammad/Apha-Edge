from typing import Any


def success_response(data: Any, request_id: str = "") -> dict[str, Any]:
    return {
        "data": data if isinstance(data, dict) else data,
        "meta": {"request_id": request_id},
    }
