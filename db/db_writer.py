

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import re 
from utils.price_simplifier import PriceSimplifier
import mysql.connector
import logging
from gmail.fetch_emails import get_gmail_service, fetch_ses_emails
from parser.gemini_parser import GeminiParser
from dotenv import load_dotenv  # 导入 dotenv
from datetime import datetime
import base64
import json


# .envファイルを読み込む
load_dotenv()

# .envからMySQL設定を取得
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

def get_db_connection():
    if not all([MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE]):
        print("MySQLの設定が不足しています。確認してください。")
        return None, None
    
    try:
        # MySQLに接続
        print("正在尝试连接到数据库...")
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        
        # 接続成功時にカーソルを作成
        print("データベース接続成功")
        cursor = conn.cursor()
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"データベース接続失敗: {err}")
        return None, None
    except Exception as e:
        print(f"設定読み込み失敗: {e}")
        return None, None

def insert_email_to_db(email_data):
    conn, cursor = get_db_connection()
    
    # データベース接続に失敗した場合、処理を中止する
    if conn is None or cursor is None:
        print("データベース接続に失敗しました。処理を中止します。")
        return
    
    try:
        print(f"準備插入数据: {email_data}")
        # PriceSimplifierのインスタンス作成
        price_simplifier = PriceSimplifier()

        unit_price_raw = email_data.get('unit_price', '')
        if isinstance(unit_price_raw, list):
            unit_price_raw = ', '.join(unit_price_raw)


        # 単価を簡略化
        simplified_price = price_simplifier.simplify_price(unit_price_raw)

        # データ挿入用SQLクエリ
        insert_query = """
            INSERT INTO ses_projects (
                received_at, subject, sender_email, 
                project_description, required_skills, optional_skills, location,
                unit_price
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # データの準備
        data = (
            email_data['received_at'],
            email_data['subject'],
            email_data['sender_email'],
            email_data['project_description'],
            ', '.join(email_data['required_skills']),
            ', '.join(email_data['optional_skills']),
            email_data['location'],
            simplified_price  # 簡略化された単価
        )
        
        # SQLクエリを実行
        cursor.execute(insert_query, data)
        
        # トランザクションをコミット
        conn.commit()
        
        print(f"{cursor.rowcount} 行のデータを正常に挿入しました。")

    except mysql.connector.Error as err:
        print(f"データベースエラー: {err}")
    finally:
        # 接続を閉じる
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


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

    except Exception as e:
        logging.error(f"主程序执行时发生错误: {str(e)}")
if __name__ == "__main__":        
    main()
        




