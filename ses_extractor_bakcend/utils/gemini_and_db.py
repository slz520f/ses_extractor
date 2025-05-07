
# ses_extractor_bakcend/utils/gemini_and_db.py
import logging
import google.generativeai as genai
from typing import List, Dict, Any 
import json
import re
import os
import time
from supabase import create_client, Client
from datetime import datetime
from .emails_helper import extract_body, extract_headers, format_datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 日志配置
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)

class GeminiParser:
    def __init__(self, model_name: str = "gemini-1.5-flash-latest", api_key: str = None):
        if api_key:
            genai.configure(api_key=api_key)
            logger.info("✅ GeminiParser 内で API キーを構成しました。")
        else:
            logger.warning("⚠️ GeminiParser に API キーが渡されませんでした。環境変数が使用されます。")
        logger.info(f"Using Gemini model: {model_name}")
        self.model = genai.GenerativeModel(model_name)

    def _construct_prompt(self, text: str) -> str:
        return f"""请严格按照以下要求从邮件文本中提取信息：

输入文本：
{text}

提取规则：
1. 每个案件以"▼"或"◆"开头
2. 按以下格式提取每个案件的信息：
{{
  "案件内容": "案件描述",
  "必須スキル": ["技能1", "技能2"],
  "勤務地": "工作地点",
  "単価": "薪资信息"
}}

输出要求：
- 必须是有效的JSON数组
- 不要包含任何额外解释
- 如果字段不存在则留空
- 薪资信息只保留第一个价格（如"600万円～900万円" → "600万円"）

示例输出：
[
  {{
    "案件内容": "データ分析業務",
    "必須スキル": ["Python", "SQL"],
    "勤務地": "東京",
    "単価": "時給2000円"
  }}
]"""

    @staticmethod
    def normalize_price(price_str: str) -> str:
        if not price_str:
            return ""
        price_str = price_str.split("～")[0].split(",")[0]
        match = re.search(r"(\d+\.?\d*)(万?円|万円|円)", price_str)
        return f"{match.group(1)}{match.group(2)}" if match else price_str

    def parse_email(self, text: str) -> List[Dict[str, Any]]:
        try:
            # 尝试使用Gemini API解析
            return self._parse_with_gemini(text)
        except Exception as e:
            logger.error(f"Gemini解析失败，使用备用解析: {str(e)}")
            return self._fallback_parse(text)

    def _parse_with_gemini(self, text: str) -> List[Dict[str, Any]]:
        response = self.model.generate_content(self._construct_prompt(text))
        output = getattr(response, 'text', str(response))
        output = output.replace("```json", "").replace("```", "").strip()
        
        logger.debug(f"Gemini原始响应:\n{output}")
        
        try:
            parsed = json.loads(output)
            if isinstance(parsed, dict):
                return [self._validate_project(parsed)]
            return [self._validate_project(p) for p in parsed]
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                return [self._validate_project(json.loads(json_match.group(0)))]
            raise

    def _fallback_parse(self, text: str) -> List[Dict[str, Any]]:
        """针对真实邮件格式的增强解析"""
        projects = []
        
        # 分割不同案件 - 根据实际邮件的分隔符
        project_sections = re.split(r'(?:\n|^)(?:■|◆)(.+?)\n', text)[1:]
        
        for i in range(0, len(project_sections), 2):
            if i+1 >= len(project_sections):
                continue
                
            title = project_sections[i].strip()
            content = project_sections[i+1]
            
            project = {
                "案件内容": title,
                "必須スキル": [],
                "尚可スキル": [],
                "勤務地": "",
                "単価": ""
            }
            
            # 提取薪资
            salary_match = re.search(r'\[ *給与 *\] (.+)', content)
            if salary_match:
                project["単価"] = self.normalize_price(salary_match.group(1))
            
            # 提取工作地点
            location_match = re.search(r'\[ *場所 *\] (.+)', content)
            if location_match:
                project["勤務地"] = location_match.group(1).strip()
            
            projects.append(project)
        
        return projects if projects else [{
            "案件内容": text[:200] + "..." if len(text) > 200 else text,
            "必須スキル": [],
            "勤務地": "",
            "単価": ""
        }]

    def _validate_project(self, project: Dict[str, Any]) -> Dict[str, Any]:
        for field in ["案件内容", "必須スキル", "勤務地", "単価"]:
            project.setdefault(field, "")
        
        if isinstance(project["必須スキル"], str):
            project["必須スキル"] = [s.strip() for s in project["必須スキル"].split(',') if s.strip()]
        
        project["単価"] = self.normalize_price(project["単価"])
        return project

# 新增存储原始邮件的函数
def save_raw_email(message_id: str, email_data: dict) :
    """存储原始邮件到raw_emails表"""
    try:
        if not message_id or not email_data:
            logger.warning(f"无效参数: message_id={message_id}, email_data={bool(email_data)}")
            return None
            
        insert_data = {
            "message_id": str(message_id)[:100],  # 限制长度
            "raw_data": json.dumps(email_data, ensure_ascii=False),

        }
        
        response = supabase.table('raw_emails') \
            .insert(insert_data) \
            .execute()
            
        if not response.data:
            logger.error("插入原始邮件失败: 无返回数据")
            return None
            
        logger.info(f"存储原始邮件成功: ID={response.data[0]['id']}")
        return response.data[0]['id']
        
    except Exception as e:
        logger.error(f"存储原始邮件失败 - message_id={message_id}: {str(e)}", exc_info=True)
        return None



def parse_emails_with_gemini(emails: List[dict], progress_callback=None, api_key=None) -> List[Dict]:
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Gemini APIキーが必要です。")

    genai.configure(api_key=api_key)
    parser = GeminiParser(api_key=api_key)
    results = []

    for i, email in enumerate(emails, 1):
        if progress_callback:
            progress_callback(i / len(emails))

        logger.info(f"\n--- 处理邮件 {i}/{len(emails)} ---")
        
        try:
            # 在解析前存储原始邮件（添加这1行）
            raw_email_id = save_raw_email(email.get('id'), email)
            if not raw_email_id:
                logger.warning(f"⚠️ 邮件 {email.get('id')} 原始内容存储失败，跳过处理")
                continue
            # 提取邮件基本信息
            subject = extract_headers(email, 'Subject')
            sender = extract_headers(email, 'From')
            date = format_datetime(extract_headers(email, 'Date'))
            body = extract_body(email)

            if not body.strip():
                logger.warning("⚠️ 空正文，跳过")
                continue

            # 解析邮件正文
            projects = parser.parse_email(body)
            logger.debug(f"解析出的项目数: {len(projects)}")
            
            # 为每个项目构建完整数据
            for idx, project in enumerate(projects, 1):
                project_data = {
                    'received_at': date,
                    'subject': f"{subject} (案件{idx})" if len(projects) > 1 else subject,
                    'sender_email': sender,
                    'project_description': project.get("案件内容", ""),
                    'required_skills': project.get("必須スキル", []),
                    'optional_skills': project.get("尚可スキル", []),
                    'location': project.get("勤務地", ""),
                    'unit_price': project.get("単価", ""),
                    'message_id': email.get('id', f"gen_{int(time.time())}_{i}_{idx}"),
                    'project_index': idx,
                    'raw_email_id': raw_email_id,  # 添加这1个新字段
                    'original_message_id': email.get('id')  # 新增原始消息ID
                }
                logger.debug(f"项目{idx}数据: {json.dumps(project_data, ensure_ascii=False)}")
                results.append(project_data)

        except Exception as e:
            logger.error(f"邮件处理失败: {str(e)}", exc_info=True)

    return results

def send_to_api(email_data_list):
    if not email_data_list:
        logger.warning("⚠️ 无数据需要插入")
        return

    success = error = 0
    
    for data in email_data_list:
        try:
            # 数据预处理
            insert_data = {
                "message_id": data['message_id'],
                "received_at": datetime.strptime(
                    data['received_at'], "%Y-%m-%d %H:%M:%S"
                ).isoformat(),
                "subject": str(data.get('subject', '無題'))[:200],
                "sender_email": str(data.get('sender_email', ''))[:100],
                "project_description": str(data.get('project_description', '無案件描述'))[:500],
                "required_skills": list_to_str(data.get('required_skills', []))[:500],
                "optional_skills": list_to_str(data.get('optional_skills', []))[:500],
                "location": str(data.get('location', ''))[:100],
                "unit_price": str(data.get('unit_price', ''))[:100],
                "project_index": int(data.get('project_index', 0)),
                "raw_email_id": data.get('raw_email_id'),
                "original_message_id": data.get('original_message_id')  # 新增字段
            }

            logger.debug(f"准备插入数据: message_id={insert_data['message_id']}, project_index={insert_data['project_index']}")

            # 检查是否存在（更精确的查询）
            exists = supabase.table('ses_projects') \
                .select('*', count='exact') \
                .eq('message_id', insert_data['message_id']) \
                .eq('project_index', insert_data['project_index']) \
                .eq('raw_email_id', insert_data['raw_email_id']) \
                .execute()

            if exists.count == 0:
                # 插入数据（使用单条插入确保原子性）
                response = supabase.table('ses_projects').insert(insert_data).execute()
                
                if response.data and len(response.data) > 0:
                    success += 1
                    logger.info(f"插入成功: {insert_data['message_id']}-{insert_data['project_index']}")
                else:
                    error += 1
                    logger.error(f"插入失败: {getattr(response, 'error', '未知错误')}")
            else:
                logger.info(f"记录已存在，跳过: {insert_data['message_id']}-{insert_data['project_index']}")

        except Exception as e:
            error += 1
            logger.error(f"数据库操作失败 - message_id={data.get('message_id')}, project_index={data.get('project_index')}: {str(e)}", 
                        exc_info=True)

    logger.info(f"处理结果: 成功={success}, 失败={error}")
    return success, error

def list_to_str(value, delimiter=", ", max_length=None):
    if isinstance(value, list):
        joined = delimiter.join(str(item) for item in value)
        return joined[:max_length] if max_length else joined
    return str(value)[:max_length] if max_length else str(value)