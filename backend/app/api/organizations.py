from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.utils import generate_invite_code, slugify
from app.db.session import get_db
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember, OrgRole
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationOut,
    OrganizationJoin,
    MembershipOut,
)

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED)
def create_organization(
    org_in: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base_slug = slugify(org_in.name)
    if not base_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name must contain at least one letter or number",
        )

    slug = base_slug
    suffix = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    new_org = Organization(
        name=org_in.name,
        slug=slug,
        invite_code=generate_invite_code(),
    )
    db.add(new_org)
    db.flush()

    membership = OrganizationMember(
        user_id=current_user.id,
        organization_id=new_org.id,
        role=OrgRole.admin,
    )
    db.add(membership)

    db.commit()
    db.refresh(new_org)

    return new_org
@router.post("/join", response_model=OrganizationOut, status_code=status.HTTP_200_OK)
def join_organization(
    join_in: OrganizationJoin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = (
        db.query(Organization)
        .filter(Organization.invite_code == join_in.invite_code)
        .first()
    )

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code",
        )

    membership = OrganizationMember(
        user_id=current_user.id,
        organization_id=org.id,
        role=OrgRole.member,
    )

    db.add(membership)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization",
        )

    db.refresh(org)
    return org


@router.get("/me", response_model=List[MembershipOut])
def list_my_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    memberships = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == current_user.id)
        .all()
    )
    return memberships

