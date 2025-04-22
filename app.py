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
from sheets.export_to_sheets import export_to_sheet, get_db_data

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

# Streamlit 页面配置
st.set_page_config(page_title="SES案件管理システム", layout="wide")

st.title('📩 SES案件管理システム')

st.markdown("これは **Gmail + Gemini + MySQL + Google Sheets** を組み合わせたSES案件抽出ツールです。")

st.divider()

# 🔐 Google认证
st.subheader("🔐 Google アカウント認証")

if 'credentials' not in st.session_state:
    if st.button('Googleでログイン'):
        creds = get_gmail_service()
        st.session_state['credentials'] = creds
        st.success("✅ ログイン成功しました！")
else:
    st.success("✅ すでにログイン済みです。")

st.divider()

# 📥 获取邮件与解析
st.header("📥 メール取得・解析")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### ① GmailからSESメールを取得")
    if st.button('メールを取る'):
        if 'credentials' in st.session_state:
            service = get_gmail_service()
            progress_bar = st.progress(0)  # 进度条初始化
            emails = fetch_ses_emails(service, progress_bar)  # 获取邮件
            st.session_state['emails'] = emails
            st.success(f"📨 メールの抽出が完了しました！共{len(emails)}件")
        else:
            st.error("⚠️ 先にログインしてください")

with col2:
    st.markdown("### ② メール内容をGeminiで解析")
    if st.button('メール内容を抽出'):
        if 'emails' not in st.session_state:
            st.error("📭 メールを先に取得してください")
        else:
            emails = st.session_state['emails']
            progress_bar = st.progress(0)
            parser = GeminiParser()
            email_data_list = []

            for i, email in enumerate(emails, 1):
                progress_bar.progress(i / len(emails))  # 更新进度条
                parsed_data = parser.parse(email)  # 解析邮件
                email_data_list.append(parsed_data)

            st.session_state['email_data_list'] = email_data_list
            st.success("🧠 Gemini解析が完了しました！")

st.divider()

# 💾 写入数据库
st.header("💾 データベース保存")
if st.button('データベースに書き込む'):
    if 'email_data_list' not in st.session_state:
        st.error("🔍 先にメール内容を抽出してください")
    else:
        email_data_list = st.session_state['email_data_list']
        for email_data in email_data_list:
            insert_email_to_db(email_data)
        st.success("✅ データベースへの保存が完了しました！")

st.divider()

# 📊 查看数据库内容
st.header("📊 データベース内容の確認")
df = get_db_data()
if df.empty:
    st.warning("📭 データがまだ登録されていません")
else:
    st.dataframe(df)

st.divider()

# 📤 导出到Google Sheets
st.header("📤 Google Sheetsへのエクスポート")
spreadsheet_id = st.text_input('📝 Google SheetsのスプレッドシートIDを入力してください')

if st.button('Google Sheetsに書き込む'):
    if spreadsheet_id:
        if 'credentials' in st.session_state:
            export_to_sheet(spreadsheet_id)
            st.success("✅ Google Sheetsへの出力が完了しました")
        else:
            st.error("🔐 先にログインしてください")
    else:
        st.error("🆔 スプレッドシートIDを入力してください")
