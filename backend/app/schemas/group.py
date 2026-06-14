from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class MemberAdd(BaseModel):
    user_id: str
    joined_at: date
    role: str = "member"


class MemberUpdate(BaseModel):
    left_at: Optional[date] = None
    role: Optional[str] = None


class MemberOut(BaseModel):
    id: str
    user_id: str
    display_name: str
    email: str
    role: str
    joined_at: date
    left_at: Optional[date] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class GroupOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_by: str
    created_at: datetime
    member_count: int = 0
    members: List[MemberOut] = []

    class Config:
        from_attributes = True


class GroupListOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    member_count: int = 0
    your_balance: float = 0.0

    class Config:
        from_attributes = True
