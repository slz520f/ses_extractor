# email_utils.py
from datetime import datetime, timedelta
import time
import re
import base64
import json
import os
import requests
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from supabase import create_client
from logging_config import setup_logger
from email_utils_helpers import  format_datetime
from gemini_parser import parse_emails_with_gemini, send_to_api

# Supabaseクライアントの初期化
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
logger = setup_logger()

# グローバル変数としてtoken_storeを定義
token_store = {}


def get_recent_emails():
    """
    获取近14天的邮件数据
    :return: 返回邮件列表
    """
    # 获取当前时间和5天前的时间
    five_days_ago = (datetime.utcnow() - timedelta(days=14)).isoformat()

    # 查询 ses_projects 表，筛选出接收时间在近5天内的记录
    response = supabase.table('ses_projects') \
        .select('*') \
        .filter('received_at', 'gte', five_days_ago) \
        .execute()

    if response.status_code == 200:
        return response.data  # 返回查询到的邮件数据
    else:
        return {"error": "查询失败", "message": response.message}



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

# def get_today_date_query():
#     """当日限定の検索クエリを作成する関数"""
#     today = datetime.now()
#     tomorrow = today + timedelta(days=1)

#     after_str = today.strftime('%Y/%m/%d')
#     before_str = tomorrow.strftime('%Y/%m/%d')

#     return f'after:{after_str} before:{before_str}' 



def fetch_ses_emails(access_token: str, progress_bar=None,query="(案件 OR SE OR 求人   ) has:nouserlabels "):
    """当日受信したSES案件メール（添付ファイルなし）を取得"""
    two_weeks_ago = datetime.now() - timedelta(days=14)
    after_str = two_weeks_ago.strftime('%Y/%m/%d')
    full_query = f"{query} after:{after_str}"

    # 使用 access_token 创建凭证对象
    credentials = Credentials(token=access_token)
    # 初始化 Google API 客户端
    service = build('gmail', 'v1', credentials=credentials)
    # 确保 service 是一个正确的 API 客户端对象
    print(f"Service type: {type(service)}")  # 确保这里输出的是 <class 'googleapiclient.discovery.Resource'>
    print(f"実行クエリ: {full_query}")

    # メールメッセージ一覧を取得
    results = service.users().messages().list(
        userId='me', 
        q=full_query, 
        maxResults=2000  # 最大2000件
    ).execute()

    messages = results.get('messages', [])
    ses_emails = []


    for msg_meta in messages:
        # 各メッセージの詳細を取得

        msg = service.users().messages().get(
            userId='me', 
            id=msg_meta['id'], 
            format='full'
        ).execute()

        # 添付ファイルがあるかチェック
        parts = msg.get('payload', {}).get('parts', [])
        has_attachment = any(
            part.get('filename') and part['filename'] != '' 
            for part in parts
        )

        # 添付ファイルなしのメールのみ追加
        if not has_attachment:
            ses_emails.append(msg)

    return ses_emails


