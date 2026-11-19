from fastapi import APIRouter, Depends, HTTPException
from app.models.models import User
from app.schemas.users import UserRead
from app.services.auth import current_user
router = APIRouter()

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, user: User = Depends(current_user)):
    if user_id != user.id:
        raise HTTPException(404, "User not found")
    return user
