from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from app.config.settings import settings
from app.services.auth_service import create_access_token, verify_token
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Initialize OAuth
oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    }
)


def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get current user from token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login"""
    try:
        # Validate OAuth configuration
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth credentials are not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your environment variables."
            )
        
        # Construct the callback URL
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/auth/google/callback"
        
        # Check if OAuth client is registered
        if not hasattr(oauth, 'google') or oauth.google is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth client not properly initialized"
            )
        
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in google_login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google OAuth login: {str(e)}"
        )


@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    try:
        token = await oauth.google.authorize_access_token(request)
        
        # Get user info - authlib may include it in token or we need to fetch it
        user_info = token.get("userinfo")
        if not user_info:
            # Try to get user info from the token response
            user_info = await oauth.google.parse_id_token(request, token)
        
        # If still no user_info, fetch it using the access token
        if not user_info:
            resp = await oauth.google.get("https://www.googleapis.com/oauth2/v2/userinfo", token=token)
            user_info = resp.json()
        
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information"
            )
        
        # Validate email domain - restrict to @lftechnology.com
        user_email = user_info.get("email", "")
        allowed_domain = "@lftechnology.com"
        
        if not user_email or not user_email.endswith(allowed_domain):
            logger.warning(f"Login attempt from unauthorized domain: {user_email}")
            frontend_url = settings.FRONTEND_URL
            # Redirect to login page with error message
            response = RedirectResponse(
                url=f"{frontend_url}/login?error=unauthorized_domain",
                status_code=303
            )
            return response
        
        # Create JWT token with user info
        access_token = create_access_token(
            data={
                "sub": user_info.get("email") or user_info.get("sub"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
            }
        )
        
        # Redirect to frontend with token
        frontend_url = settings.FRONTEND_URL
        response = RedirectResponse(url=f"{frontend_url}/auth/callback?token={access_token}")
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}"
        )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "email": current_user.get("email"),
        "name": current_user.get("name"),
        "picture": current_user.get("picture"),
    }


@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token removal)"""
    return {"message": "Logged out successfully"}
