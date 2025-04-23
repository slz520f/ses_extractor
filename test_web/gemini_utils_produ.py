import logging
import json
from typing import List, Dict
from typing import Dict, Any
import logging
from .gmail_utils import extract_headers, extract_body, format_datetime
import os
import re
import streamlit as st

import google.generativeai as genai
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


def parse_emails_with_gemini(emails: List[dict], progress_callback=None) -> List[Dict]:
    parser = GeminiParser()
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
