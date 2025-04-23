import base64
import json
import re
from datetime import datetime, timedelta
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_headers(msg, name):
    """メールヘッダから特定のフィールドを抽出"""
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
    
    # フォールバック：直接body.dataをデコード
    if 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return msg.get('snippet', '')

def format_datetime(gmail_date):
    """日付のフォーマット"""
    try:
        # JSTなどのタイムゾーン名を取り除く
        gmail_date = re.sub(r'\s*\(.*\)$', '', gmail_date)
        return datetime.strptime(gmail_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.error(f"日付のフォーマットに失敗しました: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    

def get_today_date_query():
    """当日限定の検索クエリを作成する関数"""
    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    after_str = today.strftime('%Y/%m/%d')
    before_str = tomorrow.strftime('%Y/%m/%d')

    return f'after:{after_str} before:{before_str}'    

def fetch_ses_emails(service, progress_bar=None,query="(案件 OR SE OR 求人   ) has:nouserlabels "):
    """当日受信したSES案件メール（添付ファイルなし）を取得"""
    date_query = get_today_date_query()
    full_query = f" {query}{date_query}"
    
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
