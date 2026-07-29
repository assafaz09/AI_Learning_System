from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db import get_db
from app.models import User
from app.schemas.progress import ProgressDashboardResponse
from app.services.progress_metrics import build_progress_dashboard

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("", response_model=ProgressDashboardResponse)
def get_progress_dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return build_progress_dashboard(db, user.id)
