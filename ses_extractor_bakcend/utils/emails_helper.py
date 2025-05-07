#ses_extractor_bakcend/utils/emails_helper.py
import base64
import logging
from datetime import datetime
import re

def decode_base64(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    except Exception as e:
        logging.error(f"Base64 decode failed: {e}")
        return ''
    
def extract_plain_text_from_parts(parts):
    """递归从 parts 中提取 text/plain"""
    for part in parts:
        mime_type = part.get('mimeType', '')
        body = part.get('body', {})
        if mime_type == 'text/plain' and 'data' in body:
            return decode_base64(body['data'])
        # 如果子部分中还有 parts，则递归
        if 'parts' in part:
            result = extract_plain_text_from_parts(part['parts'])
            if result:
                return result
    return ''
    
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
        return decode_base64(payload['body']['data'])
    
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
    
def simplify_gmail_message(msg: dict) -> dict:
    """提取有用字段并构建简化结构，便于后续统一保存"""
    simplified = {
        "id": msg.get("id"),
        "payload": {
            "headers": [
                {"name": "Subject", "value": extract_headers(msg, "Subject")},
                {"name": "From", "value": extract_headers(msg, "From")},
                {"name": "Date", "value": extract_headers(msg, "Date")}
            ],
            "body": {
                "data": extract_body(msg)
            }
        }
    }
    return simplified
