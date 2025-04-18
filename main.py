# main.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from gmail.fetch_emails import get_gmail_service, fetch_ses_emails
from parser.gemini_parser import GeminiParser
from db.db_writer import insert_email_to_db
from sheets.export_to_sheets import export_to_sheet,get_db_data
import base64
import json
from datetime import datetime
import logging

from dotenv import load_dotenv
load_dotenv()

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_headers(msg, name):
    """从邮件头中提取特定字段"""
    headers = msg.get('payload', {}).get('headers', [])
    for h in headers:
        if h.get('name', '').lower() == name.lower():
            return h.get('value', '')
    return ''

def extract_body(msg) -> str:
    """从Gmail消息中提取纯文本正文"""
    payload = msg.get('payload', {})
    
    # 尝试从parts中提取
    parts = payload.get('parts', [])
    for part in parts:  
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')
    
    # 回退方案：直接解码body.data
    if 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return msg.get('snippet', '')

def format_datetime(gmail_date):
    """格式化日期"""
    try:
        return datetime.strptime(gmail_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.error(f"日期格式化失败: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def main():
    logging.info("🔍 正在从Gmail获取邮件...")
    
    try:
        # 第一步：获取 Gmail 服务对象并获取邮件
        service = get_gmail_service()
        emails = fetch_ses_emails(service)
        
        if not emails:
            logging.warning("📭 未找到今日邮件")
            return
        
        logging.info(f"\n📩 找到 {len(emails)} 封符合条件的邮件")
        
        parser = GeminiParser()
        email_data_list = []  # 用于存储所有处理后的邮件数据

        # 第二步：处理每封邮件
        for i, email in enumerate(emails, 1):
            logging.info(f"\n--- 处理邮件 {i}/{len(emails)} ---")
            
            # 提取元数据
            subject = extract_headers(email, 'Subject')
            sender = extract_headers(email, 'From')
            date = format_datetime(extract_headers(email, 'Date'))
            body_text = extract_body(email)

            logging.info(f"主题: {subject}")
            logging.info(f"发件人: {sender}")
            logging.info(f"日期: {date}")
            
            if not body_text.strip():
                logging.warning("⚠️ 正文为空，跳过")
                continue
            
            # 解析内容
            try:
                parsed = parser.parse_email(body_text)
                logging.info("解析结果:")
                logging.info(json.dumps(parsed, indent=2, ensure_ascii=False))
                
                # 准备数据库数据
                email_data = {
                    'received_at': date,
                    'subject': subject,
                    'sender_email': sender,
                    'project_description': parsed.get('案件内容', ''),  # リストをカンマ区切りの文字列に変換
                    # 'required_skills': ', '.join(parsed.get('必須スキル', [])),  # リストをカンマ区切りの文字列に変換
                    # 'optional_skills': ', '.join(parsed.get('尚可スキル', [])),  # リストをカンマ区切りの文字列に変換
                    'required_skills': parsed.get('必須スキル', []),
                    'optional_skills': parsed.get('尚可スキル', []),
                    "location": parsed.get("勤務地", ""),
                    "unit_price": parsed.get("単価", "") 
                }
                
                # 存储处理后的数据，准备写入数据库
                email_data_list.append(email_data)
            
            except Exception as e:
                logging.error(f"❌ 处理邮件时失败: {str(e)}")
        
        # 第三步：将数据写入数据库
        if email_data_list:
            logging.info("📤 开始写入数据库...")
            for email_data in email_data_list:
                insert_email_to_db(email_data)
            logging.info("✅ 所有数据已存入数据库")
        
        # 第四步：将数据导出到 Google Sheets
        if email_data_list:
            logging.info("📊 开始将数据导出到Google Sheets...")

            
            SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

            if not SPREADSHEET_ID:
                print("❌ SPREADSHEET_ID 未定义，请检查 .env 文件是否正确加载")
            else:
                print(f"🔧 使用的 SPREADSHEET_ID: {SPREADSHEET_ID}")
                # 确保将 SPREADSHEET_ID 传递给 export_to_sheet
                export_to_sheet(SPREADSHEET_ID)
            logging.info("✅ 数据已成功导出到 Google Sheets")

    except Exception as e:
        logging.error(f"主程序执行时发生错误: {str(e)}")

if __name__ == "__main__":
    main()        



