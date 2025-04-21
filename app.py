import streamlit as st
import pandas as pd
import os
import json
import pickle
import base64
import logging
import re
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# これらは4つのモジュールのインポート
from gmail.fetch_emails import fetch_ses_emails
from parser.gemini_parser import GeminiParser
from db.db_writer import insert_email_to_db
from sheets.export_to_sheets import export_to_sheet,get_db_data

# Google認証に必要なスコープ
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/spreadsheets']

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

# ヘッダー
st.title('SES案件管理システム')

# Google 認証を処理する関数
def get_gmail_service():
    """Gmail APIサービスを取得する関数"""
    creds = None
    # 以前のトークンが存在する場合は読み込み
    if os.path.exists('gmail/token.pickle'):
        with open('gmail/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # 認証が無効または存在しない場合は再取得
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())  # リフレッシュトークンで更新
        else:
            # 新規認証フロー開始
            flow = InstalledAppFlow.from_client_secrets_file('/Users/mame/ses_extractor/config/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # トークンを保存
        with open('/Users/mame/ses_extractor/gmail/token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    # Gmail APIサービスをビルドして返す
    service = build('gmail', 'v1', credentials=creds)
    return service

# Google ログイン
if 'credentials' not in st.session_state:
    st.header('Google アカウントでログイン')
    if st.button('ログイン'):
        creds = get_gmail_service()
        st.session_state['credentials'] = creds
        st.success("ログイン成功しました！")

# 提取邮件按钮
if st.button('メールを取る'):
    if 'credentials' in st.session_state:
        # fetch_emails() 関数を呼び出してメールを取得
        service = get_gmail_service()
        emails = fetch_ses_emails(service)
        st.session_state['emails'] = emails  # ✅ 保存到 session_state
        st.success("メールの抽出が完了しました！")
    else:
        st.error("Googleアカウントでログインしてください")
    parser = GeminiParser()
    email_data_list = []    

# 筛选邮件按钮
if st.button('メール内容を抽出'):
    if 'emails' not in st.session_state:
        st.error("先に『提取邮件』を実行してください")
    else:
        emails = st.session_state['emails']
        parser = GeminiParser()
        email_data_list = []

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
        st.session_state['email_data_list'] = email_data_list
        st.success("メールのフィルタリングが完了しました！")

# 写入数据库按钮
if st.button('データベースに書き込む'):
    if 'email_data_list' not in st.session_state:
        st.error("先に『筛选邮件』を実行してください")
    else:
        email_data_list = st.session_state['email_data_list']
        logging.info("📤 データベースに書き込みを開始します...")
        for email_data in email_data_list:
            insert_email_to_db(email_data)
        logging.info("✅ すべてのデータがデータベースに書き込まれました")
        st.success("データベースへの書き込みが完了しました！")

# 写入Google Sheets按钮
st.header('Google Sheetsへのエクスポート')
spreadsheet_id = st.text_input('Google SheetsのスプレッドシートIDを入力', '')
if st.button(' Google Sheetsに書き込む'):
    if spreadsheet_id:
        if 'credentials' in st.session_state:
            export_to_sheet(spreadsheet_id)
            st.success("データがGoogle Sheetsにエクスポートされました")
        else:
            st.error("先にGoogleアカウントでログインしてください")
    else:
        st.error("Google SheetsのIDを入力してください")

# データベースのデータを表示
st.header('データベースのデータ')
df = get_db_data()
if df.empty:
    st.warning("データがありません")
else:
    st.dataframe(df)
