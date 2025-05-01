from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
import requests
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
        five_days_ago = (datetime.utcnow() - timedelta(days=14)).isoformat()
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



def refresh_access_token(refresh_token: str):
    """使用 refresh_token 获取新的 access_token"""
    token_url = "https://oauth2.googleapis.com/token"
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("缺少 GOOGLE_CLIENT_ID 或 GOOGLE_CLIENT_SECRET 环境变量。")
    
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = requests.post(token_url, data=payload)
    
    if response.status_code == 200:
        tokens = response.json()
        return tokens.get("access_token")
    else:
        raise Exception(f"Token刷新失败: {response.text}")
    
def get_today_date_query():
    """当日限定の検索クエリを作成する関数"""
    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    after_str = today.strftime('%Y/%m/%d')
    before_str = tomorrow.strftime('%Y/%m/%d')

    return f'after:{after_str} before:{before_str}'    

def fetch_ses_emails(access_token: str, query="(案件 OR SE OR 求人) has:nouserlabels"):
# def fetch_ses_emails(access_token: str, query=" has:nouserlabels"):

    # 获取上次时间
    last_status = get_last_fetch_status()
    after_str = ""
    if last_status:
        last_time = datetime.fromisoformat(last_status["last_fetch_time"])
        after_str = f"after:{last_time.strftime('%Y/%m/%d')}"  # Gmail 的 after 是日期粒度
    else:
        after_str = f"after:{(datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')}"

    full_query = f"{query} {after_str}"
    
    credentials = Credentials(token=access_token)
    service = build('gmail', 'v1', credentials=credentials)
    
    print(f"实用查询: {full_query}")
    results = service.users().messages().list(userId='me', q=full_query, maxResults=2000).execute()
    
    messages = results.get('messages', [])
    ses_emails = []

    latest_internal_date = None
    latest_message_id = None
    
    for msg_meta in messages:
        msg = service.users().messages().get(userId='me', id=msg_meta['id'], format='full').execute()

        internal_date = int(msg.get('internalDate', 0))
        if latest_internal_date is None or internal_date > latest_internal_date:
            latest_internal_date = internal_date
            latest_message_id = msg.get('id')

        parts = msg.get('payload', {}).get('parts', [])
        has_attachment = any(
            part.get('filename') and part['filename'] != '' for part in parts
        )
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
            return data[0]
    except Exception as e:
        print("DEBUG: Error while accessing response.data:", e)

    return None


def update_fetch_status(last_message_id, last_time):
    supabase.table("email_fetch_status").insert({
        "last_fetch_time": last_time,
        "last_message_id": last_message_id
    }).execute()
