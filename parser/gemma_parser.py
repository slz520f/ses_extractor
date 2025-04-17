# parser/gemma_parser.py
import json
from dotenv import load_dotenv
import os
import re
from typing import Dict, Any
import logging

# .env 読み込み
load_dotenv()

import google.generativeai as genai
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GemmaParser:
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

if __name__ == "__main__":
    parser = GemmaParser()
    print("✅ gemma_parser.py 正常启动")
    
    
    
#     sample_text = """
# 【案件タイトル】金融システム開発プロジェクト

# 【業務内容】
# 銀行向け決済システムの設計・開発業務
# - 要求分析・基本設計
# - Javaによる詳細設計・実装
# - 単体テスト・結合テストの実施

# 【必須スキル】
# - Java (Spring Boot) 3年以上
# - SQL (Oracle, PostgreSQL)
# - 基本設計書作成経験

# 【尚可スキル】
# - 金融領域知識
# - Docker/Kubernetes
# - マイクロサービスアーキテクチャ

# 【勤務地】
# 東京都千代田区（リモート可：週2回出社）

# 【単価】
# ¥750,000〜850,000/月

# 【その他】
# プロジェクト期間：2024年9月〜2025年3月
# """
    
#     result = parser.parse_email(sample_text)
#     print("解析結果:")
#     print(json.dumps(result, indent=2, ensure_ascii=False))
