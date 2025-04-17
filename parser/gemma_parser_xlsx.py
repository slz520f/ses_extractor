import json
import time
import re
import pandas as pd
from typing import Dict, Any
import logging
import google.generativeai as genai

# Google Generative AI API 配置
genai.configure(api_key="AIzaSyBIcNmE1dX4pIolZHlOFoCQ7oEBRyEOfxU")

# 日志配置
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class GemmaParser:
    def __init__(self, model_name: str = "gemini-1.5-flash-latest"):
        """
        Google Generative AI (Gemini) 模型初始化
        
        Args:
            model_name (str): 模型名称
        """
        logger.info(f"Using Gemini model: {model_name}")
        self.model = genai.GenerativeModel(model_name)

    def _construct_prompt(self, text: str) -> str:
        """
        构建解析邮件的 prompt（清晰的日文指示）
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
        解析模型输出的内容，提取 JSON 部分
        """
        logger.debug(f"受信したモデル出力:\n{output}")  # 输出模型原始返回结果
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
        解析邮件正文，返回结构化数据
        
        Args:
            text (str): 邮件正文文本
            
        Returns:
            dict: 解析结果（出错时返回默认值）
        """
        prompt = self._construct_prompt(text)
        
        retries = 5  # 重试次数
        retry_delay = 13  # 初始重试延迟（秒）

        for attempt in range(retries):
            try:
                response = self.model.generate_content(prompt)
                output = response.text.strip()
                logger.debug(f"模型生出力:\n{output}")
                return self._parse_output(output)
            except Exception as e:
                if "429" in str(e):  # 检查是否是 429 错误
                    logger.warning(f"请求过于频繁，等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)  # 等待一段时间后重试
                    retry_delay *= 2  # 每次重试时增加等待时间
                else:
                    logger.error(f"预期外的错误发生: {str(e)}")
                    break
        
        return {
            "案件内容": "",
            "必須スキル": [],
            "尚可スキル": [],
            "勤務地": "",
            "単価": ""
        }

if __name__ == "__main__":
    # 读取 Excel 文件并处理每一条案件数据
    file_path = 'ダミー案件20件.xlsx'  # 更新为文件的实际路径
    df = pd.read_excel(file_path)
    
    parser = GemmaParser()
    print("✅ gemma_parser.py 正常启动")

    # 假设每一行有一个 'メール本文' 列，存储案件的邮件内容
    for index, row in df.iterrows():
        text = row['本文']  # 确保列名与实际的 Excel 文件一致
        print(f"正在解析第 {index + 1} 行案件：")
        
        # 调用 parse_email 解析每一条邮件内容
        result = parser.parse_email(text)
        print("解析结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("="*50)  # 输出分隔符，方便查看

    
    
    
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
