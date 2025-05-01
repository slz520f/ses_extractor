import logging
import google.generativeai as genai
from typing import List, Dict, Any 
import json
import re
import os
from supabase import create_client, Client
from datetime import datetime
from .emails_helper import extract_body, extract_headers, format_datetime
# 日志配置
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
GMAIL_API_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

class GeminiParser:
    def __init__(self, model_name: str = "gemini-1.5-flash-latest", api_key: str = None):
        """
        Google Generative AI (Gemini) モデルの初期化

        Args:
            model_name (str): モデル名
            api_key (str): 明示的に渡された API キー（オプション）
        """
        if api_key:
            genai.configure(api_key=api_key)
            logger.info("✅ GeminiParser 内で API キーを構成しました。")
        else:
            logger.warning("⚠️ GeminiParser に API キーが渡されませんでした。環境変数が使用されます。")
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



#有增量的parse_emails_with_gemini
def parse_emails_with_gemini(emails: List[dict], progress_callback=None, api_key=None) -> List[Dict]:
    import google.generativeai as genai


    if api_key:
        genai.configure(api_key=api_key)
        logger.info("✅ 明示された API キーで Gemini を構成しました。")
    else:
        env_key = os.getenv("GOOGLE_API_KEY")
        if env_key:
            genai.configure(api_key=env_key)
            logger.info("✅ 環境変数から API キーを読み取りました。")
            api_key = env_key  # パーサーにも渡すため
        else:
            logger.error("❌ Gemini APIキーが見つかりません。")
            raise ValueError("Gemini APIキーが必要です。")


    parser = GeminiParser(api_key=api_key)  # パーサーにも渡す
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
    # 初始化Supabase客户端
    supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
    success_count = 0
    error_count = 0
    
    for email_data in email_data_list:
        try:
            # 强化数据预处理
            data = {
                "message_id": email_data['message_id'],
                "received_at": datetime.strptime(email_data['received_at'], "%Y-%m-%d %H:%M:%S").isoformat(),
                "subject": str(email_data.get('subject', '')),
                "sender_email": str(email_data.get('sender_email', '')),
                "project_description": list_to_str(email_data.get('project_description', []))or "无案件描述",  # 默认值处理
                "required_skills": list_to_str(email_data.get('required_skills', [])),
                "optional_skills": list_to_str(email_data.get('optional_skills', [])),
                "location": list_to_str(email_data.get('location', [])),
                "unit_price": list_to_str(email_data.get('unit_price', []), max_length=500)  # 防止超长
            }

            # 在插入前进行检查和默认值填充
            if not data["project_description"]:
                data["project_description"] = "无案件描述"  # 默认值
                # 检查message_id是否已存在于数据库中
            existing_data = supabase.table('ses_projects').select('message_id').eq('message_id', data['message_id']).execute()

            if existing_data.data and len(existing_data.data) > 0:
                # 如果已经存在，则跳过插入
                logger.info(f"✅ 数据已存在，跳过插入: {data['message_id']}")
                continue  # 跳过本次循环

            # 插入数据到 Supabase
            response = supabase.table('ses_projects').insert(data).execute()


            
            # 检查是否插入成功
            if response.data and len(response.data) > 0:
                success_count += 1
                logger.info(f"✅ 数据插入成功: {email_data['message_id']}")
            else:
                error_count += 1
                logger.error(f"❌ 数据插入失败: {response.error}")
                # 输出更多的错误信息
                if response.error:
                    logger.error(f"❌ 返回的错误信息: {response.error}")
                
        except Exception as e:
            error_count += 1
            logger.error(f"⚠️ 数据库操作异常: {str(e)}")
            # 输出异常的详细信息
            logger.error(f"⚠️ 异常详情: {e}")
    
    logger.info(f"处理完成: 成功{success_count}条, 失败{error_count}条")
                
  

def list_to_str(value, delimiter=", ", max_length=None):
    """安全处理列表转字符串"""
    if isinstance(value, list):
        joined = delimiter.join(str(item) for item in value)
        return joined[:max_length] if max_length else joined
    return str(value)[:max_length] if max_length else str(value)