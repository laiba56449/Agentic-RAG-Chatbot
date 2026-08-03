from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.api.deps import (
    get_current_user,
    require_org_member,
    require_org_admin,
)
from app.models.user import User
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember, OrgRole
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationOut,
    OrganizationJoin,
    MembershipOut,
)
from app.core.utils import slugify, generate_invite_code


router = APIRouter(
    prefix="/api/organizations",
    tags=["organizations"]
)


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

    existing = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == org.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this organization",
        )

    membership = OrganizationMember(
        user_id=current_user.id,
        organization_id=org.id,
        role=OrgRole.member,
    )

    db.add(membership)

    db.commit()
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


@router.get("/{org_id}/member-check")
def member_check(
    membership: OrganizationMember = Depends(require_org_member),
):
    return {
        "organization_id": str(membership.organization_id),
        "role": membership.role.value,
    }


@router.get("/{org_id}/admin-check")
def admin_check(
    membership: OrganizationMember = Depends(require_org_admin),
):
    return {
        "organization_id": str(membership.organization_id),
        "role": membership.role.value,
    }