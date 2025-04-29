from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import requests
import os
import re
import logging
import google.generativeai as genai
import json
import base64
from typing import Dict, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv
from routers.auth import token_store
from supabase import create_client  # 导入 supabase 客户端
from typing import List, Dict, Any  # Ensure List is imported
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# 初始化
router = APIRouter()
load_dotenv()

# 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

# 日志配置
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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

def fetch_ses_emails(access_token: str, progress_bar=None,query="(案件 OR SE OR 求人   ) has:nouserlabels "):
    """当日受信したSES案件メール（添付ファイルなし）を取得"""
    date_query = get_today_date_query()
    full_query = f" {query}{date_query}"

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

class GeminiParser:
    def __init__(self, model_name: str = "gemini-1.5-flash-latest"):
        """
        Google Generative AI (Gemini) モデルの初期化
        
        Args:
            model_name (str): モデル名
        """
        logger.info(f"Using Gemini model: {model_name}")
        self.model = genai.GenerativeModel(model_name)

    def _construct_prompt(self, text: str) -> str:
        """
        プロンプトの構築（日本語で明確な指示）
        """
        return f"""以下はSES案件メールの本文です。以下の項目を日本語で抽出し、JSON形式で返してください。

### 抽出項目:
- 案件内容（仕事の詳細）
- 必須スキル（必須技術・資格）
- 尚可スキル（あれば良い技術）
- 勤務地（都道府県または市区町村）
- 単価（"¥"や"円"を含む文字列）

### 出力形式:
{{
  "案件内容": "...",
  "必須スキル": ["...", "..."],
  "尚可スキル": ["...", "..."],
  "勤務地": "...",
  "単価": "..."
}}

### メール本文:
{text}

### JSON出力:"""

    def _parse_output(self, output: str) -> Dict[str, Any]:
        """
        モデルの生出力からJSON部分を抽出
        """
        json_match = re.search(r'\{[\s\S]*\}', output)
        if not json_match:
            raise ValueError("出力にJSONが見つかりません")
        
        json_str = json_match.group(0)
        
        try:
            parsed = json.loads(json_str)
            required_fields = ["案件内容", "必須スキル", "勤務地", "単価"]
            for field in required_fields:
                if field not in parsed:
                    raise ValueError(f"必須フィールド '{field}' が見つかりません")
                    
            if isinstance(parsed["必須スキル"], str):
                parsed["必須スキル"] = [s.strip() for s in parsed["必須スキル"].split(",") if s.strip()]
            if isinstance(parsed.get("尚可スキル", []), str):
                parsed["尚可スキル"] = [s.strip() for s in parsed["尚可スキル"].split(",") if s.strip()]
                
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}\n出力内容: {output}")
            raise

    def parse_email(self, text: str) -> Dict[str, Any]:
        """
        メール本文を解析して構造化データを返す
        
        Args:
            text (str): メール本文テキスト
            
        Returns:
            dict: 解析結果（エラー時はデフォルト値が入る）
        """


        

        prompt = self._construct_prompt(text)

        try:
            response = self.model.generate_content(prompt)
            output = response.text.strip()
            logger.debug(f"モデル生出力:\n{output}")
            return self._parse_output(output)
            
        except Exception as e:
            logger.error(f"予期せぬエラー: {str(e)}")
        return {
            "案件内容": "",
            "必須スキル": [],
            "尚可スキル": [],
            "勤務地": "",
            "単価": ""
        }


def parse_emails_with_gemini(emails: List[dict], progress_callback=None, api_key=None) -> List[Dict]:
    import google.generativeai as genai

    # APIキーの構成（引数優先、なければ環境変数）
    if api_key:
        genai.configure(api_key=api_key)
        logger.info("✅ 明示された API キーで Gemini を構成しました。")
    else:
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            genai.configure(api_key=env_key)
            logger.info("✅ 環境変数から API キーを読み取りました。")
        else:
            logger.error("❌ Gemini APIキーが見つかりません。")
            raise ValueError("Gemini APIキーが必要です。")

    parser = GeminiParser()  # パーサーにも渡す
    email_data_list = []

    for i, email in enumerate(emails, 1):
        if progress_callback:
            progress_callback(i / len(emails))

        logging.info(f"\n--- メール {i}/{len(emails)} を処理中 ---")
        
        subject = extract_headers(email, 'Subject')
        sender = extract_headers(email, 'From')
        date = format_datetime(extract_headers(email, 'Date'))
        body_text = extract_body(email)

        logging.info(f"件名: {subject}")
        logging.info(f"送信者: {sender}")
        logging.info(f"日付: {date}")

        if not body_text.strip():
            logging.warning("⚠️ 本文が空です。スキップします。")
            continue

        try:
            parsed = parser.parse_email(body_text)
            logging.info("解析結果:")
            logging.info(json.dumps(parsed, indent=2, ensure_ascii=False))

            email_data = {
                'received_at': date,
                'subject': subject,
                'sender_email': sender,
                'project_description': parsed.get('案件内容', ''),
                'required_skills': parsed.get('必須スキル', []),
                'optional_skills': parsed.get('尚可スキル', []),
                "location": parsed.get("勤務地", ""),
                "unit_price": parsed.get("単価", ""),
                'message_id': email.get('id')
            }

            email_data_list.append(email_data)

        except Exception as e:
            logging.error(f"❌ メールの処理中にエラーが発生しました: {str(e)}")

    return email_data_list

def send_to_api(email_data_list):
    url = "http://127.0.0.1:8000/projects/"  # FastAPI的URL
    headers = {"Content-Type": "application/json"}
    success_count = 0
    error_count = 0
    
    for email_data in email_data_list:
        try:
            # 强化数据预处理
            processed_data = {
                "message_id": email_data['message_id'],
                "received_at": datetime.strptime(email_data['received_at'], "%Y-%m-%d %H:%M:%S").isoformat(),
                "subject": str(email_data.get('subject', '')),
                "sender_email": str(email_data.get('sender_email', '')),
                "project_description": list_to_str(email_data.get('project_description', [])),
                "required_skills": list_to_str(email_data.get('required_skills', [])),
                "optional_skills": list_to_str(email_data.get('optional_skills', [])),
                "location": list_to_str(email_data.get('location', [])),
                "unit_price": list_to_str(email_data.get('unit_price', []), max_length=500)  # 防止超长
            }

            # 发送请求
            response = requests.post(url, json=processed_data, headers=headers)
            result = response.json()
            
            # 增强响应处理
            if response.status_code == 200:
                if result.get("status") == "success":
                    success_count += 1
                    print(f"✅ {result.get('action', '操作')}成功: {processed_data['message_id']}")
                else:
                    error_count += 1
                    print(f"❌ 业务错误: {result.get('reason', '未知原因')}")
            else:
                error_count += 1
                print(f"❌ HTTP错误 [{response.status_code}]: {response.text}")
                
        except Exception as e:
            error_count += 1
            print(f"⚠️ 请求异常: {str(e)}")

def list_to_str(value, delimiter=", ", max_length=None):
    """安全处理列表转字符串"""
    if isinstance(value, list):
        joined = delimiter.join(str(item) for item in value)
        return joined[:max_length] if max_length else joined
    return str(value)[:max_length] if max_length else str(value)

# 获取 SES 邮件接口
@router.get("/fetch_emails")
async def fetch_emails():
    access_token = token_store.get("access_token")
    logger.info(f"Access token: {access_token}")
    if not access_token:
        raise HTTPException(status_code=401, detail="未登录或Token已失效")
    
    # 调用 Gmail API 来验证访问令牌是否有效
    response = requests.get(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    # 输出日志来查看响应
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response body: {response.text}")

    # 检查 API 返回状态
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="无法获取邮件")

    # 1. 获取邮件
    ses_emails = fetch_ses_emails(access_token)

    return JSONResponse(content={"messages": ses_emails})

# 解析所有邮件并保存到数据库
@router.post("/parse_and_save_all_emails")
async def parse_and_save_all_emails():
    access_token = token_store.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="未登录或Token已失效")

   # 获取邮件（直接调用 fetch_ses_emails）
    ses_emails = fetch_ses_emails(access_token)

    # 使用Gemini解析
    email_data_list = parse_emails_with_gemini(ses_emails)

    # 发送到API或保存数据库
    send_to_api(email_data_list)

    return JSONResponse(content={"status": "success", "processed_count": len(email_data_list)})

