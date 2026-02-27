"""
Authentication endpoints: login, register, profile.
"""
from fastapi import APIRouter, HTTPException, status, Depends

from models.user import UserRegister, UserLogin, UserProfile, UserProfileUpdate, TokenResponse
from services import supabase_service as db
from utils.helpers import create_access_token, get_current_user_id

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister):
    """Register a new user account."""
    try:
        # Create user in Supabase Auth
        auth_user = db.create_user_auth(payload.email, payload.password)
        user_id = auth_user["id"]

        # Create profile record
        profile = db.create_profile(
            user_id=user_id,
            full_name=payload.full_name,
            email=payload.email,
            exam_target=payload.exam_target or "JEE Main",
        )

        # Generate JWT
        token = create_access_token(data={"sub": user_id, "email": payload.email})

        return TokenResponse(
            access_token=token,
            user=UserProfile(
                id=user_id,
                full_name=profile.get("full_name", payload.full_name),
                email=profile.get("email", payload.email),
                avatar_url=profile.get("avatar_url"),
                exam_target=profile.get("exam_target", "JEE Main"),
                created_at=profile.get("created_at"),
            ),
        )
    except Exception as e:
        error_msg = str(e)
        if "already" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {error_msg}",
        )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin):
    """Login with email and password."""
    try:
        # Sign in via Supabase Auth
        session = db.sign_in_user(payload.email, payload.password)
        user_id = session["user_id"]

        # Get profile
        try:
            profile = db.get_user_profile(user_id)
        except Exception:
            profile = {"id": user_id, "email": payload.email, "full_name": "User"}

        # Generate our own JWT
        token = create_access_token(data={"sub": user_id, "email": payload.email})

        return TokenResponse(
            access_token=token,
            user=UserProfile(
                id=user_id,
                full_name=profile.get("full_name", "User"),
                email=profile.get("email", payload.email),
                avatar_url=profile.get("avatar_url"),
                exam_target=profile.get("exam_target", "JEE Main"),
                created_at=profile.get("created_at"),
            ),
        )
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Login failed: {error_msg}",
        )


@router.get("/profile", response_model=UserProfile)
async def get_profile(user_id: str = Depends(get_current_user_id)):
    """Get the current user's profile."""
    try:
        profile = db.get_user_profile(user_id)
        return UserProfile(**profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    payload: UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
):
    """Update the current user's profile."""
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    try:
        updated = db.update_user_profile(user_id, updates)
        profile = db.get_user_profile(user_id)
        return UserProfile(**profile)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}",
        )
