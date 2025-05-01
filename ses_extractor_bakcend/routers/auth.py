from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
import os
from dotenv import load_dotenv
import requests
from fastapi import APIRouter, HTTPException, Request
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token




load_dotenv()

router = APIRouter()

# Google OAuth2设置
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/spreadsheets",
    "openid",
]
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL")

# 测试用Token存储（后面可以换成DB或Supabase）
token_store = {}



@router.get("/login")
async def login():
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
        access_type="offline",  # 获取refresh_token
        include_granted_scopes="true"
    )
    return JSONResponse(content={"redirect_url": auth_url})

@router.get("/callback")
async def auth_callback(request: Request):
    state = request.query_params.get("state")
    code = request.query_params.get("code")
    if not code:
        return JSONResponse(content={"error": "No code provided"}, status_code=400)

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

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # 获取用户信息
        user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {
            "Authorization": f"Bearer {credentials.token}",
        }
        user_info_response = requests.get(user_info_url, headers=headers)

        if user_info_response.status_code != 200:
            return JSONResponse(content={"error": "Failed to fetch user info"}, status_code=500)

        user_info = user_info_response.json()
        user_email = user_info.get("email")

        print(f"用户信息：{user_info}")

        # 可以将access_token、refresh_token等存入数据库
        token_store["access_token"] = credentials.token
        token_store["refresh_token"] = credentials.refresh_token
        token_store["user_email"] = user_email

        # ✅ 登录成功后，重定向到前端主页并附带必要的信息
        frontend_home_url = "http://localhost:3000/auth/callback" 
        # frontend_home_url = "https://ses-extractor-1.onrender.com/auth/callback"
        return RedirectResponse(url=f"{frontend_home_url}/?email={user_email}&access_token={credentials.token}")

    except Exception as e:
        print(f"Error fetching token or user info: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)