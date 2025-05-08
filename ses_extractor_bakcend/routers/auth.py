from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
import os
from dotenv import load_dotenv
import requests
import logging
import secrets
from services.auth_service import AuthService
from datetime import datetime, timedelta, timezone
from typing import Annotated

# 初始化
load_dotenv()
router = APIRouter()
auth_service = AuthService()
logger = logging.getLogger(__name__)

# 配置
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/spreadsheets",
    "openid",
]



@router.get("/login")
async def login():
    """初始化OAuth2流程"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true"
    )
    
    return JSONResponse(content={"redirect_url": auth_url})

@router.get("/callback")
async def auth_callback(request: Request):
    """OAuth2回调处理"""
    code = request.query_params.get("code")
    if not code:
        logger.error("Authorization code missing")
        return JSONResponse(
            content={"error": "缺少授权码"}, 
            status_code=400
        )

    try:
        # 获取token
        logger.debug("Initializing Flow...")
        flow = Flow.from_client_config(
            {"web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uris": [GOOGLE_REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }},
            scopes=SCOPES,
        )
        flow.redirect_uri = GOOGLE_REDIRECT_URI
        logger.debug("Fetching token...")
        flow.fetch_token(code=code) 
        
        # 获取用户信息
        logger.debug("Getting user info...")
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {flow.credentials.token}"}
        ).json()
        logger.debug(f"User info: {user_info}")
        
        user_email = user_info.get("email")
        if not user_email:
            raise ValueError("无法获取用户邮箱")
        
        # トークン情報を準備
        token_data = {
            "token": flow.credentials.token,
            "refresh_token": flow.credentials.refresh_token,
            "expires_in": (flow.credentials.expiry - datetime.now()).total_seconds(),
            "expires_at": flow.credentials.expiry.isoformat()
        }
        
        # 存储token并生成JWT
        logger.debug(f"Storing tokens for {user_email}...")
        auth_service.store_tokens(user_email, token_data)
        logger.debug("Generating JWT...")
        jwt_token = auth_service.create_jwt(user_email)
        
        logger.info(f"用户 {user_email} 登录成功")
        
        # フロントエンドのURL設定
        frontend_home_url = "http://localhost:3000/auth/callback" 
        # frontend_home_url = "https://ses-extractor-1.onrender.com/auth/callback"
        return RedirectResponse(url=f"{frontend_home_url}/?email={user_email}&access_token={jwt_token}")
   
        

    except Exception as e:
        logger.error(f"回调处理失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail={
            "error": "authentication_failed",
            "message": str(e)
        })