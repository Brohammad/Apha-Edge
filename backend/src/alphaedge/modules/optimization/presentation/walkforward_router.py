"""Walk-forward visualization API."""

from fastapi import APIRouter, Depends, Request
from alphaedge.dependencies import get_current_user_id
from alphaedge.shared.presentation.envelope import success_response

walkforward_router = APIRouter(prefix="/optimization", tags=["Optimization"])


@walkforward_router.get("/walk-forward/{run_id}")
async def walk_forward_viz(run_id: str, request: Request, _user=Depends(get_current_user_id)):
    windows = [
        {"window": i, "in_sample_sharpe": 1.2 + i * 0.05, "out_sample_sharpe": 0.9 + i * 0.03}
        for i in range(1, 6)
    ]
    return success_response({"run_id": run_id, "windows": windows}, request_id=getattr(request.state, "request_id", ""))
