from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse


import os
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from routers.auth import token_store
from supabase import create_client, Client
from typing import Set

from utils.emails import fetch_ses_emails, refresh_access_token
from utils.gemini_and_db import parse_emails_with_gemini, send_to_api



# 初始化
router = APIRouter()

load_dotenv()

# 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# 日志配置
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_parsed_message_ids() -> Set[str]:
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
    result = supabase.table("ses_projects").select("message_id").execute()
    ids = set(item["message_id"] for item in result.data if item.get("message_id"))
    return ids


# 获取 SES 邮件接口
@router.get("/fetch_emails")
async def fetch_emails():
    access_token = token_store.get("access_token")
    refresh_token = token_store.get("refresh_token")
    logger.info(f"Access token: {access_token}")
    if not access_token:
        raise HTTPException(status_code=401, detail="未登录或Token已失效")

    try:
        emails = fetch_ses_emails(access_token)
        return {"emails": emails}

    except Exception as e:
        # 处理token过期
        if "invalid_grant" in str(e) or "Invalid Credentials" in str(e) or "401" in str(e):
            logger.warning("Access token 已过期，尝试刷新...")
            if not refresh_token:
                raise HTTPException(status_code=401, detail="Refresh token 不存在，无法刷新。")
            
            try:
                new_access_token = refresh_access_token(refresh_token)
                token_store["access_token"] = new_access_token
                logger.info("✅ Access token 刷新成功，重新尝试fetch邮件...")
                
                # 刷新后重新尝试
                emails = fetch_ses_emails(new_access_token)
                return {"emails": emails}
            
            except Exception as refresh_error:
                logger.error(f"Token刷新失败: {str(refresh_error)}")
                raise HTTPException(status_code=401, detail="Token刷新失败，请重新登录。")
        else:
            logger.error(f"未知错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")
    


# 解析所有邮件并保存到数据库
@router.post("/parse_and_save_all_emails")
async def parse_and_save_all_emails():
    access_token = token_store.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="未登录或Token已失效")

    # 获取邮件
    ses_emails = fetch_ses_emails(access_token)
    total_fetched = len(ses_emails)
    logging.info(f"📥 抓取到的邮件总数: {total_fetched}")

    # 获取已经解析过的 message_id
    parsed_ids = get_parsed_message_ids()
    logging.info(f"📂 数据库中已存在的解析记录数: {len(parsed_ids)}")

    # 过滤掉已解析的邮件
    unparsed_emails = [email for email in ses_emails if email.get("id") not in parsed_ids]
    logging.info(f"🧹 过滤后未解析邮件数: {len(unparsed_emails)}")
    logging.info(f"♻️ 重复（已解析）邮件数: {total_fetched - len(unparsed_emails)}")

    if not unparsed_emails:
        logging.info("✅ 没有新邮件需要解析。")
        return JSONResponse(content={
            "status": "success", 
            "processed_count": 0, 
            "message": "没有新邮件需要解析",
            "logs": {
                "total_fetched": total_fetched,
                "parsed_count": len(parsed_ids),
                "unparsed_count": 0,
                "duplicate_count": total_fetched,
                "processed_count": 0,
                "message": "没有新邮件需要解析"
            }
        })

    # 使用Gemini解析
    email_data_list = parse_emails_with_gemini(unparsed_emails)

    # 发送到API或保存数据库
    send_to_api(email_data_list)

    logging.info(f"✅ 实际解析并写入的邮件数: {len(email_data_list)}")

    return JSONResponse(content={
        "status": "success",
        "processed_count": len(email_data_list),
        "logs": {
            "total_fetched": total_fetched,
            "parsed_count": len(parsed_ids),
            "unparsed_count": len(unparsed_emails),
            "duplicate_count": total_fetched - len(unparsed_emails),
            "processed_count": len(email_data_list),
            "message": "解析成功"
        }
    })





@router.get("/recent")
async def get_recent_emails():
    """
    获取近5天的邮件数据（修复版）
    """
    try:
        # 获取当前时间（带时区信息）
        now = datetime.now(timezone.utc)
        five_days_ago = now - timedelta(days=5)

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
    


@router.get("/test")
async def test_endpoint():
    return {"message": "测试端点正常工作"}