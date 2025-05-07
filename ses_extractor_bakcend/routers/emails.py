# ses_extractor_bakcend/routers/emails.py
from fastapi import APIRouter, HTTPException,Depends
from fastapi.responses import JSONResponse
from fastapi import Request
import os
import re
import json
from pydantic import BaseModel
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
from typing import Optional
from typing import Dict
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

class RawEmailData(BaseModel):
    body: str
    headers: Dict[str, str]

class RawEmailResponse(BaseModel):
    success: bool
    data: RawEmailData



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
    

@router.get("/recent")
async def get_recent_emails():
    """
    获取近14天的邮件数据（修复版）
    """
    try:
        # 获取当前时间（带时区信息）
        now = datetime.now(timezone.utc)
        five_days_ago = now - timedelta(days=14)

        logger.info(f"查询时间范围: {five_days_ago.isoformat()} 至 {now.isoformat()}")



       # 查询数据库
        response = supabase.table('ses_projects') \
            .select('*') \
            .gte('received_at', five_days_ago.isoformat()) \
            .order('received_at', desc=True) \
            .execute()

        # 检查错误
        if hasattr(response, 'error') and response.error:
            logger.error(f"Supabase查询错误: {response.error}")
            raise HTTPException(status_code=500, detail="数据库查询失败")

        logger.info(f"查询到 {len(response.data)} 条记录")
        return {"emails": response.data}

    except Exception as e:
        logger.error(f"获取近期邮件失败: {str(e)}")
        raise HTTPException(status_code=500, detail="获取近期邮件失败")




@router.get("/get_raw_email/{raw_email_id}", response_model=RawEmailResponse)
async def get_raw_email(
    raw_email_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        jwt_token = credentials.credentials
        # await verify_jwt(jwt_token)

        # 查询数据库
        logger.info(f"🔍 查询原始邮件 ID: {raw_email_id}")
        result = supabase.table('raw_emails').select('*').eq('id', raw_email_id).maybe_single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="指定ID的原始邮件不存在")

        raw_email = result.data
        raw_data = raw_email.get("raw_data")
        
        # 记录完整原始数据（调试用）
        logger.info(f"完整原始数据: {raw_data}")

        try:
            email_json = json.loads(raw_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="原始邮件数据格式无效")

        # 关键修正：从payload层级提取数据
        payload = email_json.get("payload", {})
        logger.info(f"Payload数据: {payload}")

        # 处理headers
        headers_list = payload.get("headers", [])
        headers_dict = {h.get("name"): h.get("value") for h in headers_list 
                       if isinstance(h, dict) and "name" in h and "value" in h}

        # 处理body
        body_data = payload.get("body", {}).get("data", "")
        
        # Base64解码处理
        if isinstance(body_data, str) and body_data.startswith("base64:"):
            import base64
            try:
                body_data = base64.b64decode(body_data[7:]).decode("utf-8")
              
            except Exception as e:
                logger.warning(f"Base64解码失败: {str(e)}")
                body_data = "（正文解码失败）"

        # 构建响应
        response_data = {
            "success": True,
            "data": {
                "headers": headers_dict,
                "body": body_data,
                "metadata": {
                    "message_id": raw_email.get("message_id"),
                    "stored_at": raw_email.get("created_at")
                }
            }
        }

        logger.info(f"处理后的响应数据: {response_data}")
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取原始邮件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")