#ses_extractor_bakcend/utils/emails.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
from fastapi import HTTPException

# 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
def get_recent_emails():
    """
    获取近14天的邮件数据
    :return: 返回邮件列表
    """
    try:
        # 计算14天前的UTC时间
        five_days_ago = (datetime.utcnow() - timedelta(days=14)).isoformat()
        # 查询Supabase数据库
        response = supabase.table('ses_projects') \
            .select('*') \
            .filter('received_at', 'gte', five_days_ago) \
            .execute()

        if response.error is None:
            return response.data
        else:
            raise Exception(f"查询失败: {response.error.message}")
    except Exception as e:
        return {"error": "查询失败", "message": str(e)}
    
    
def get_today_date_query():
    """当日限定の検索クエリを作成する関数"""
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    # 格式化日期字符串
    after_str = today.strftime('%Y/%m/%d')
    before_str = tomorrow.strftime('%Y/%m/%d')

    return f'after:{after_str} before:{before_str}'    # 返回Gmail搜索语法

def fetch_ses_emails(access_token: str, query="(案件 OR SE OR 求人) has:nouserlabels"):
# def fetch_ses_emails(access_token: str, query=" has:nouserlabels"):

    # 获取上次时间
    last_status = get_last_fetch_status()
    after_str = ""
    # 根据上次抓取时间构建时间范围查询
    if last_status:
        last_time = datetime.fromisoformat(last_status["last_fetch_time"])
        after_str = f"after:{last_time.strftime('%Y/%m/%d')}"  # Gmail 的 after 是日期粒度
    else:
        after_str = f"after:{(datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')}"

    full_query = f"{query} {after_str}"# 组合完整查询条件
    # 初始化Gmail服务
    credentials = Credentials(token=access_token)
    service = build('gmail', 'v1', credentials=credentials)
    
    print(f"实用查询: {full_query}")
    # 执行邮件列表查询
    results = service.users().messages().list(userId='me', q=full_query, maxResults=200).execute()
    
    messages = results.get('messages', [])# 获取邮件列表
    ses_emails = []# 存储符合条件的邮件

    latest_internal_date = None # 记录最新的邮件日期
    latest_message_id = None# 记录最新的邮件ID
    # 遍历处理每封邮件
    for msg_meta in messages:
        # 获取完整邮件内容
        msg = service.users().messages().get(userId='me', id=msg_meta['id'], format='full').execute()
        # 更新最新邮件信息
        internal_date = int(msg.get('internalDate', 0))
        if latest_internal_date is None or internal_date > latest_internal_date:
            latest_internal_date = internal_date
            latest_message_id = msg.get('id')
        # 检查邮件是否包含附件
        parts = msg.get('payload', {}).get('parts', [])
        has_attachment = any(
            part.get('filename') and part['filename'] != '' for part in parts
        )
        # 不含附件的邮件加入结果列表
        if not has_attachment:
            ses_emails.append(msg)

    # 如果有抓到邮件，更新状态
    if latest_internal_date and latest_message_id:
        last_time = datetime.utcfromtimestamp(latest_internal_date / 1000)
        update_fetch_status(latest_message_id, last_time.isoformat())

    return ses_emails


def get_last_fetch_status():
    response = supabase.table("email_fetch_status").select("*").order("created_at", desc=True).limit(1).execute()
    
    try:
        data = response.data
        if data:
            return data[0]# 返回最新记录
    except Exception as e:
        print("DEBUG: Error while accessing response.data:", e)

    return None


def update_fetch_status(last_message_id, last_time):
    """
    更新邮件抓取状态到数据库
    参数:
        last_message_id: 最新邮件的ID
        last_time: 最新邮件的时间戳
    """
    supabase.table("email_fetch_status").insert({
        "last_fetch_time": last_time,
        "last_message_id": last_message_id
    }).execute()
