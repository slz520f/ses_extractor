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
import re

from dotenv import load_dotenv
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

def main():
    logging.info("🔍 Gmailからメールを取得しています...")
    
    try:
        # ステップ1：Gmailサービスオブジェクトを取得し、メールを取得
        service = get_gmail_service()
        emails = fetch_ses_emails(service)
        
        if not emails:
            logging.warning("📭 今日のメールが見つかりませんでした")
            return
        
        logging.info(f"\n📩 {len(emails)} 件の該当するメールが見つかりました")
        
        parser = GeminiParser()
        email_data_list = []  # 処理済みのメールデータを格納するリスト

        # ステップ2：各メールを処理
        for i, email in enumerate(emails, 1):
            logging.info(f"\n--- メール {i}/{len(emails)} を処理中 ---")
            
            # メタデータを抽出
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
            
            # 内容を解析
            try:
                parsed = parser.parse_email(body_text)
                logging.info("解析結果:")
                logging.info(json.dumps(parsed, indent=2, ensure_ascii=False))
                
                # データベース用のデータを準備
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
                
                # 処理したデータを格納し、データベースに書き込む準備
                email_data_list.append(email_data)
            
            except Exception as e:
                logging.error(f"❌ メールの処理中にエラーが発生しました: {str(e)}")
        
        # ステップ3：データベースにデータを書き込む
        if email_data_list:
            logging.info("📤 データベースに書き込みを開始します...")
            for email_data in email_data_list:
                insert_email_to_db(email_data)
            logging.info("✅ すべてのデータがデータベースに書き込まれました")
        
        # ステップ4：データをGoogle Sheetsにエクスポート
        if email_data_list:
            logging.info("📊 データをGoogle Sheetsにエクスポートしています...")

            
            SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

            if not SPREADSHEET_ID:
                print("❌ SPREADSHEET_IDが定義されていません。.envファイルが正しく読み込まれているか確認してください。")
            else:
                print(f"🔧 使用するSPREADSHEET_ID: {SPREADSHEET_ID}")
                # SPREADSHEET_IDをexport_to_sheetに渡す
                export_to_sheet(SPREADSHEET_ID)
            logging.info("✅ データがGoogle Sheetsに正常にエクスポートされました")

    except Exception as e:
        logging.error(f"メインプログラム実行中にエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main()
