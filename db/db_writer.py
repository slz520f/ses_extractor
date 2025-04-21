

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
        print("データベースに接続中...")
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
             # 追加: MySQL 8.0以降の認証プラグイン
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

def serialize_field(value):
    """リストの場合はJSON文字列に変換、それ以外はそのまま返す"""
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return value    

def insert_email_to_db(email_data):
    conn, cursor = get_db_connection()
    
    # データベース接続に失敗した場合、処理を中止する
    if conn is None or cursor is None:
        print("データベース接続に失敗しました。処理を中止します。")
        return
    
    try:
        print(f"データを挿入する準備: {email_data}")
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
                unit_price, message_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # データの準備
        data = (
            email_data['received_at'],
            email_data['subject'],
            email_data['sender_email'],
            serialize_field(email_data.get('project_description', '')),
            serialize_field(email_data.get('required_skills', '')),
            serialize_field(email_data.get('optional_skills', '')),
            serialize_field(email_data.get('location', '')),
            simplified_price,
            email_data['message_id']
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
    """メールのヘッダーから特定のフィールドを抽出"""
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
    
    # フォールバック: body.dataを直接デコード
    if 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return msg.get('snippet', '')

def format_datetime(gmail_date):
    """日付をフォーマット"""
    try:
        # JSTなどのタイムゾーン名を取り除く
        gmail_date = re.sub(r'\s*\(.*\)$', '', gmail_date)
        return datetime.strptime(gmail_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.error(f"日付のフォーマットに失敗しました: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
def main():
    logging.info("🔍 Gmailからメールを取得中...")
    
    try:
        # 第1ステップ: Gmailサービスオブジェクトを取得し、メールを取得
        service = get_gmail_service()
        emails = fetch_ses_emails(service)
        
        if not emails:
            logging.warning("📭 今日のメールは見つかりませんでした")
            return
        
        logging.info(f"\n📩 {len(emails)} 件の該当するメールが見つかりました")
        
        parser = GeminiParser()
        email_data_list = []  # すべての処理済みメールデータを格納

          # 第2ステップ: 各メールを処理
        for i, email in enumerate(emails, 1):
            logging.info(f"\n--- メール {i}/{len(emails)} を処理中 ---")
            
             # メタデータの抽出
            subject = extract_headers(email, 'Subject')
            sender = extract_headers(email, 'From')
            date = format_datetime(extract_headers(email, 'Date'))
            body_text = extract_body(email)

            logging.info(f"件名: {subject}")
            logging.info(f"送信者: {sender}")
            logging.info(f"日付: {date}")
            
            if not body_text.strip():
                logging.warning("⚠️ 本文が空です。スキップします")
                continue
            
           # 内容を解析
            try:
                parsed = parser.parse_email(body_text)
                logging.info("解析结果:")
                logging.info(json.dumps(parsed, indent=2, ensure_ascii=False))
                
                # データベースに格納するためのデータを準備
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
                    "unit_price": parsed.get("単価", ""),
                    'message_id': email.get('id') 
                }
                
                # 処理済みデータを格納、データベースに保存する準備
                email_data_list.append(email_data)
            
            except Exception as e:
                logging.error(f"❌ メール処理中にエラーが発生しました: {str(e)}")
        
        # 第3ステップ: データをデータベースに書き込む
        if email_data_list:
            logging.info("📤 データベースに書き込み中...")
            for email_data in email_data_list:
                insert_email_to_db(email_data)
            logging.info("✅ すべてのデータがデータベースに保存されました")

    except Exception as e:
        logging.error(f"メインプログラム実行中にエラーが発生しました: {str(e)}")
if __name__ == "__main__":        
    main()
        




