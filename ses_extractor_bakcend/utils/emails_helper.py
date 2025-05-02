#ses_extractor_bakcend/utils/emails_helper.py
import base64
import logging
from datetime import datetime
import re
def extract_headers(msg, name):
    """メールヘッダから特定のフィールドを抽出"""
    # 获取消息中的headers列表(默认为空列表)
    headers = msg.get('payload', {}).get('headers', [])
    # 遍历headers查找匹配字段(不区分大小写)
    for h in headers:
        if h.get('name', '').lower() == name.lower():
            return h.get('value', '')
    return ''

def extract_body(msg) -> str:
    """Gmailメッセージからプレーンテキスト本文を抽出"""
    payload = msg.get('payload', {})
    
    # 优先从parts中查找text/plain部分
    parts = payload.get('parts', [])
    for part in parts:  
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                # 对Base64编码的内容进行URL安全解码
                return base64.urlsafe_b64decode(data).decode('utf-8')
    
    # フォールバック：直接body.dataをデコード
    if 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return msg.get('snippet', '')

def format_datetime(gmail_date):
    """日付のフォーマット"""
    try:
        # 使用正则移除括号内的时区名称
        gmail_date = re.sub(r'\s*\(.*\)$', '', gmail_date)
        # 解析Gmail日期格式(如"Wed, 15 Mar 2023 09:30:45 +0900")
        return datetime.strptime(gmail_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.error(f"日付のフォーマットに失敗しました: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')