from supabase import create_client
import os
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
import logging
import requests
from google.oauth2.credentials import Credentials
from jose import jwt

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        self.jwt_secret = os.getenv("JWT_SECRET", "default_secret")
        self.jwt_algorithm = "HS256"

    def create_jwt(self, user_email: str) -> str:
        """JWTトークンを生成"""
        return jwt.encode(
            {
                "sub": user_email,
                "exp": datetime.now() + timedelta(hours=1)
            },
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )
    
    def get_valid_token(self, user_email: str) -> str:
        """有効なアクセストークンを取得"""
        tokens = self.get_tokens(user_email)
        if not tokens:
            raise HTTPException(status_code=401, detail="ログインしていません")

        # タイムゾーンを統一して比較
        expires_at = datetime.fromisoformat(tokens["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)  # タイムゾーン付きの現在時刻
        
        if expires_at < now:
            return self.refresh_token(user_email, tokens["refresh_token"])
        
        return tokens["access_token"]
    
    def get_tokens(self, user_email: str) -> dict:
        """データベースからトークンを取得"""
        response = self.supabase.table("user_tokens")\
            .select("*")\
            .eq("user_email", user_email)\
            .single()\
            .execute()
        return response.data if response.data else None
    
    def refresh_token(self, user_email: str, refresh_token: str) -> str:
        """アクセストークンをリフレッシュ"""
        try:
            new_token = self._refresh_access_token(refresh_token)
            self._update_access_token(user_email, new_token, 3600)
            return new_token
        except Exception as e:
            logger.error(f"トークンリフレッシュ失敗: {str(e)}")
            raise HTTPException(status_code=401, detail="トークンリフレッシュに失敗しました。再度ログインしてください。")
    
    def _refresh_access_token(self, refresh_token: str) -> str:
        """実際のトークンリフレッシュ処理"""
        token_url = "https://oauth2.googleapis.com/token"
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            raise ValueError("GOOGLE_CLIENT_ID または GOOGLE_CLIENT_SECRET 環境変数が設定されていません")
        
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            return response.json().get("access_token")
        raise Exception(f"トークンリフレッシュ失敗: {response.text}")
    
    def _update_access_token(self, user_email: str, token: str, expires_in: int):
        """データベースのトークンを更新"""
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        self.supabase.table("user_tokens")\
            .update({
                "access_token": token,
                "expires_at": expires_at.isoformat()
            })\
            .eq("user_email", user_email)\
            .execute()

    def store_tokens(self, user_email: str, token_data: dict):
        """トークンをデータベースに保存"""
        try:
            expires_at = token_data["expires_at"]
            if not isinstance(expires_at, str):
                expires_at = expires_at.isoformat()
                
            # on_conflictパラメータを指定してupsert
            response = self.supabase.table("user_tokens")\
                .upsert({
                    "user_email": user_email,  # このフィールドがconflictの判定に使われる
                    "access_token": token_data["token"],
                    "refresh_token": token_data["refresh_token"],
                    "expires_at": expires_at
                }, on_conflict="user_email")\
                .execute()
            
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Supabaseエラー: {response.error.message}")
                
        except Exception as e:
            logger.error(f"トークン保存失敗: {str(e)}")
            raise