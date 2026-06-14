from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app.models.user import User
from app.models.group import Group, GroupMembership
from app.schemas.group import GroupCreate, GroupUpdate, MemberAdd, MemberUpdate, GroupOut, MemberOut, GroupListOut
from app.utils.security import get_current_user, require_group_admin
from app.services.balance import compute_group_balances

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.post("", response_model=GroupOut)
def create_group(data: GroupCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    group = Group(name=data.name, description=data.description, created_by=current_user.id)
    db.add(group)
    db.flush()

    # Auto-add creator as admin
    membership = GroupMembership(
        group_id=group.id,
        user_id=current_user.id,
        role="admin",
        joined_at=date.today(),
    )
    db.add(membership)
    db.commit()
    db.refresh(group)

    return _build_group_out(group, db)


@router.get("", response_model=list[GroupListOut])
def list_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memberships = db.query(GroupMembership).filter(GroupMembership.user_id == current_user.id).all()
    group_ids = [m.group_id for m in memberships]
    groups = db.query(Group).filter(Group.id.in_(group_ids)).order_by(Group.created_at.desc()).all()

    result = []
    for g in groups:
        member_count = db.query(GroupMembership).filter(
            GroupMembership.group_id == g.id,
            GroupMembership.left_at.is_(None),
        ).count()
        # Compute user's balance in this group
        your_balance = 0.0
        try:
            balances = compute_group_balances(db, g.id)
            your_balance = balances["balances"].get(current_user.id, 0.0)
        except Exception:
            pass
        result.append(GroupListOut(
            id=g.id, name=g.name, description=g.description,
            created_at=g.created_at, member_count=member_count,
            your_balance=your_balance,
        ))
    return result


@router.get("/{group_id}", response_model=GroupOut)
def get_group(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return _build_group_out(group, db)


@router.put("/{group_id}", response_model=GroupOut)
def update_group(group_id: str, data: GroupUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if data.name is not None:
        group.name = data.name
    if data.description is not None:
        group.description = data.description
    db.commit()
    db.refresh(group)
    return _build_group_out(group, db)


@router.delete("/{group_id}")
def delete_group(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), _admin=Depends(require_group_admin)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    db.delete(group)
    db.commit()
    return {"detail": "Group deleted"}


# --- Members ---

@router.post("/{group_id}/members", response_model=MemberOut)
def add_member(group_id: str, data: MemberAdd, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), _admin=Depends(require_group_admin)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    user = db.query(User).filter(User.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already a member
    existing = db.query(GroupMembership).filter(
        GroupMembership.group_id == group_id,
        GroupMembership.user_id == data.user_id,
        GroupMembership.left_at.is_(None),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already an active member")

    membership = GroupMembership(
        group_id=group_id,
        user_id=data.user_id,
        role=data.role,
        joined_at=data.joined_at,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return MemberOut(
        id=membership.id, user_id=user.id, display_name=user.display_name,
        email=user.email, role=membership.role, joined_at=membership.joined_at,
        left_at=membership.left_at, is_active=membership.left_at is None,
    )


@router.put("/{group_id}/members/{membership_id}", response_model=MemberOut)
def update_member(group_id: str, membership_id: str, data: MemberUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    membership = db.query(GroupMembership).filter(
        GroupMembership.id == membership_id,
        GroupMembership.group_id == group_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    if data.left_at is not None:
        membership.left_at = data.left_at
    if data.role is not None:
        membership.role = data.role
    db.commit()
    db.refresh(membership)

    user = db.query(User).filter(User.id == membership.user_id).first()
    return MemberOut(
        id=membership.id, user_id=user.id, display_name=user.display_name,
        email=user.email, role=membership.role, joined_at=membership.joined_at,
        left_at=membership.left_at, is_active=membership.left_at is None,
    )


@router.delete("/{group_id}/members/{membership_id}")
def remove_member(group_id: str, membership_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), _admin=Depends(require_group_admin)):
    membership = db.query(GroupMembership).filter(
        GroupMembership.id == membership_id,
        GroupMembership.group_id == group_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    db.delete(membership)
    db.commit()
    return {"detail": "Member removed"}


@router.get("/{group_id}/members", response_model=list[MemberOut])
def list_members(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    memberships = db.query(GroupMembership).filter(GroupMembership.group_id == group_id).all()
    result = []
    for m in memberships:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            result.append(MemberOut(
                id=m.id, user_id=user.id, display_name=user.display_name,
                email=user.email, role=m.role, joined_at=m.joined_at,
                left_at=m.left_at, is_active=m.left_at is None,
            ))
    return result


def _build_group_out(group: Group, db: Session) -> GroupOut:
    memberships = db.query(GroupMembership).filter(GroupMembership.group_id == group.id).all()
    members = []
    for m in memberships:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            members.append(MemberOut(
                id=m.id, user_id=user.id, display_name=user.display_name,
                email=user.email, role=m.role, joined_at=m.joined_at,
                left_at=m.left_at, is_active=m.left_at is None,
            ))
    return GroupOut(
        id=group.id, name=group.name, description=group.description,
        created_by=group.created_by, created_at=group.created_at,
        member_count=len([m for m in members if m.is_active]),
        members=members,
    )
