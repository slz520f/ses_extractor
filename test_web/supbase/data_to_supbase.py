import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

import re

import logging
from utils.price_simplifier import PriceSimplifier
from dotenv import load_dotenv  # 导入 dotenv
from datetime import datetime
import base64
import json
from supabase import create_client, Client

# .envファイルを読み込む
load_dotenv()

# .envからSupabase設定を取得
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Supabaseのクライアントを作成
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)




def serialize_field(value):
    """リストの場合はJSON文字列に変換、それ以外はそのまま返す"""
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return value    

def insert_email_to_db(email_data):
    # PriceSimplifierのインスタンス作成
    price_simplifier = PriceSimplifier()

    unit_price_raw = email_data.get('unit_price', '')
    if isinstance(unit_price_raw, list):
        unit_price_raw = ', '.join(unit_price_raw)

    # 単価を簡略化
    simplified_price = price_simplifier.simplify_price(unit_price_raw)

    # Supabaseにデータを挿入
    try:
        data = {
            'received_at': email_data['received_at'],
            'subject': email_data['subject'],
            'sender_email': email_data['sender_email'],
            'project_description': serialize_field(email_data.get('project_description', '')),
            'required_skills': serialize_field(email_data.get('required_skills', '')),
            'optional_skills': serialize_field(email_data.get('optional_skills', '')),
            'location': serialize_field(email_data.get('location', '')) or None,
            'unit_price': simplified_price,
            'message_id': email_data['message_id']
        }

        # Supabase に挿入
        response = supabase.table('ses_projects').insert(data).execute()

        if response.status_code == 201:
            logging.info(f"データが正常に挿入されました: {response.data}")
        else:
            logging.error(f"挿入エラー: {response.error_message}")

    except Exception as e:
        logging.error(f"データベースエラー: {str(e)}")

def extract_headers(msg, name):
    """メールのヘッダーから特定のフィールドを抽出"""
    headers = msg.get('payload', {}).get('headers', [])
    for h in headers:
        if h.get('name', '').lower() == name.lower():
            return h.get('value', '')
    return ''

def extract_body(msg) -> str:
    """Gmailメッセージからプレーンテキスト本文を抽出"""
    payload = msg.get('payload', {})
    
     # partsから抽出を試みる
    parts = payload.get('parts', [])
    for part in parts:  
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')
    
    # フォールバック: body.dataを直接デコード
    if 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return msg.get('snippet', '')

def format_datetime(gmail_date):
    """日付をフォーマット"""
    try:
        # JSTなどのタイムゾーン名を取り除く
        gmail_date = re.sub(r'\s*\(.*\)$', '', gmail_date)
        return datetime.strptime(gmail_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.error(f"日付のフォーマットに失敗しました: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


