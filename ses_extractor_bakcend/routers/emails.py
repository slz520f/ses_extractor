#ses_extractor_bakcend/routers/emails.py
from fastapi import APIRouter, HTTPException,Depends
from fastapi.responses import JSONResponse
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
# 初始化
router = APIRouter()
auth_service = AuthService()
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
    # 查询ses_projects表中所有message_id
    result = supabase.table("ses_projects").select("message_id").execute()
    # 提取非空的message_id并转为集合
    ids = set(item["message_id"] for item in result.data if item.get("message_id"))
    return ids


# 获取 SES 邮件接口
@router.get("/fetch_emails")
async def fetch_emails(user_email: str = Depends(get_current_user)):
    """获取SES邮件"""
    try:
        access_token = auth_service.get_valid_token(user_email)
        emails = fetch_ses_emails(access_token)
        logger.info(f"用户 {user_email} 获取了 {len(emails)} 封邮件")
        return {"emails": emails}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取邮件失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"邮件获取失败: {str(e)}"
        )
    
# 解析所有邮件并保存到数据库
@router.post("/parse_and_save_all_emails")
async def parse_and_save_all_emails(user_email: str = Depends(get_current_user)):
    try:
        # 获取邮件
        access_token = auth_service.get_valid_token(user_email)
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

        # 如果没有新邮件需要解析
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
    except Exception as e:
        logger.error(f"解析保存失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"邮件解析保存失败: {str(e)}"
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
    


@router.get("/test")
async def test_endpoint():
    return {"message": "测试端点正常工作"}