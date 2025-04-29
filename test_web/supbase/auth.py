from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import secrets
import os

router = APIRouter()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets"
]

CLIENT_SECRETS_FILE = 'app/config/client_secrets.json'
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8000/oauth2/callback')

@router.get("/login")
async def google_login():
    """返回 OAuth2 登录 URL"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    oauth_state = secrets.token_urlsafe(16)
    auth_url, _ = flow.authorization_url(
        prompt='consent', access_type='offline', include_granted_scopes='true'
    )
    
    return RedirectResponse(auth_url)

@router.get("/oauth2/callback")
async def oauth2_callback(code: str):
    """处理 OAuth 回调，交换 token"""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, scopes=SCOPES, redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    # 保存 credentials（如存储在数据库或 session）
    return {"access_token": creds.token, "token_type": "bearer"}

@router.get("/logout")
async def logout():
    """登出"""
    # 清除用户认证信息
    return {"status": "logged_out"}
