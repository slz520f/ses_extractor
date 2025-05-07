# ses_extractor_bakcend/routers/emails.py
from fastapi import APIRouter, HTTPException,Depends
from fastapi.responses import JSONResponse
from fastapi import Request
import json
import os
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Set
from utils.emails import fetch_ses_emails
from utils.gemini_and_db import parse_emails_with_gemini, send_to_api
from services.auth_service import AuthService
from middleware.auth import get_current_user
from typing import Union
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 初期化
router = APIRouter()
auth_service = AuthService()
load_dotenv()
security = HTTPBearer()

# 設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# ログ設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_parsed_message_ids() -> Set[str]:
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
    # ses_projectsテーブルから全てのmessage_idを取得
    result = supabase.table("ses_projects").select("message_id").execute()
    # 空でないmessage_idを抽出しセットに変換
    ids = set(item["message_id"] for item in result.data if item.get("message_id"))
    return ids


# SESメール取得API
@router.get("/fetch_emails")
async def fetch_emails(user_email: str = Depends(get_current_user)):
    """SESメールを取得"""
    try:
        access_token = auth_service.get_valid_token(user_email)
        emails = fetch_ses_emails(access_token)
        logger.info(f"ユーザー {user_email} が {len(emails)} 件のメールを取得")
        return {"emails": emails}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"メール取得失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"メール取得に失敗しました: {str(e)}"
        )
    
# 全てのメールを解析してデータベースに保存
@router.post("/parse_and_save_all_emails")
async def parse_and_save_all_emails(user_email: str = Depends(get_current_user)):
    try:
        # メールを取得
        access_token = auth_service.get_valid_token(user_email)
        ses_emails = fetch_ses_emails(access_token)
        total_fetched = len(ses_emails)
        logging.info(f"📥 取得したメール総数: {total_fetched}")

        # 既に解析済みのmessage_idを取得
        parsed_ids = get_parsed_message_ids()
        logging.info(f"📂 データベース内の解析済みレコード数: {len(parsed_ids)}")

        # 未解析のメールをフィルタリング
        unparsed_emails = [email for email in ses_emails if email.get("id") not in parsed_ids]
        logging.info(f"🧹 フィルタリング後の未解析メール数: {len(unparsed_emails)}")
        logging.info(f"♻️ 重複（解析済み）メール数: {total_fetched - len(unparsed_emails)}")

        # 新しいメールがない場合
        if not unparsed_emails:
            logging.info("✅ 解析が必要な新しいメールはありません")
            return JSONResponse(content={
                "status": "success", 
                "processed_count": 0, 
                "message": "解析が必要な新しいメールはありません",
                "logs": {
                    "total_fetched": total_fetched,
                    "parsed_count": len(parsed_ids),
                    "unparsed_count": 0,
                    "duplicate_count": total_fetched,
                    "processed_count": 0,
                    "message": "解析が必要な新しいメールはありません"
                }
            })

        # Geminiで解析
        email_data_list = parse_emails_with_gemini(unparsed_emails)

        # APIに送信またはデータベースに保存
        send_to_api(email_data_list)

        logging.info(f"✅ 実際に解析して書き込んだメール数: {len(email_data_list)}")

        return JSONResponse(content={
            "status": "success",
            "processed_count": len(email_data_list),
            "logs": {
                "total_fetched": total_fetched,
                "parsed_count": len(parsed_ids),
                "unparsed_count": len(unparsed_emails),
                "duplicate_count": total_fetched - len(unparsed_emails),
                "processed_count": len(email_data_list),
                "message": "解析に成功しました"
            }
        })
    except Exception as e:
        logger.error(f"解析保存に失敗: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"メールの解析保存に失敗しました: {str(e)}"
            )