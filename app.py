# import streamlit as st
# import pandas as pd
# import os
# import json
# import pickle
# import base64
# import logging
# import re
# from datetime import datetime
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from google.auth.transport.requests import Request

# from mysql.connector import Error



# # これらは4つのモジュールのインポート
# from gmail.fetch_emails import fetch_ses_emails
# from parser.gemini_parser import GeminiParser
# from db.db_writer import insert_email_to_db
# from sheets.export_to_sheets import export_to_sheet, get_db_data

# # Google認証に必要なスコープ
# SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/spreadsheets']

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# def extract_headers(msg, name):
#     """メールヘッダから特定のフィールドを抽出"""
#     headers = msg.get('payload', {}).get('headers', [])
#     for h in headers:
#         if h.get('name', '').lower() == name.lower():
#             return h.get('value', '')
#     return ''

# def extract_body(msg) -> str:
#     """Gmailメッセージからプレーンテキスト本文を抽出"""
#     payload = msg.get('payload', {})
    
#     # partsから抽出を試みる
#     parts = payload.get('parts', [])
#     for part in parts:  
#         if part.get('mimeType') == 'text/plain':
#             data = part.get('body', {}).get('data', '')
#             if data:
#                 return base64.urlsafe_b64decode(data).decode('utf-8')
    
#     # フォールバック：直接body.dataをデコード
#     if 'body' in payload and 'data' in payload['body']:
#         return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
#     return msg.get('snippet', '')

# def format_datetime(gmail_date):
#     """日付のフォーマット"""
#     try:
#         # JSTなどのタイムゾーン名を取り除く
#         gmail_date = re.sub(r'\s*\(.*\)$', '', gmail_date)
#         return datetime.strptime(gmail_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
#     except Exception as e:
#         logging.error(f"日付のフォーマットに失敗しました: {str(e)}")
#         return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# # Google 認証を処理する関数
# def get_gmail_service():
#     """Gmail APIサービスを取得する関数"""
#     creds = None
#     # 以前のトークンが存在する場合は読み込み
#     if os.path.exists('gmail/token.pickle'):
#         with open('gmail/token.pickle', 'rb') as token:
#             creds = pickle.load(token)
#     # 認証が無効または存在しない場合は再取得
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())  # リフレッシュトークンで更新
#         else:
#             # 新規認証フロー開始
#             flow = InstalledAppFlow.from_client_secrets_file('/Users/mame/ses_extractor/config/credentials.json', SCOPES)
#             creds = flow.run_local_server(port=0)
#         # トークンを保存
#         with open('/Users/mame/ses_extractor/gmail/token.pickle', 'wb') as token:
#             pickle.dump(creds, token)
#     # Gmail APIサービスをビルドして返す
#     service = build('gmail', 'v1', credentials=creds)
#     return service

# # Streamlit 页面配置
# st.set_page_config(page_title="SES案件管理システム", layout="wide")

# st.title('📩 SES案件管理システム')

# st.markdown("これは **Gmail + Gemini + MySQL + Google Sheets** を組み合わせたSES案件抽出ツールです。")

# st.divider()

# # 🔐 Google认证
# st.subheader("🔐 Google アカウント認証")

# if 'credentials' not in st.session_state:
#     if st.button('Googleでログイン'):
#         creds = get_gmail_service()
#         st.session_state['credentials'] = creds
#         st.success("✅ ログイン成功しました！")
# else:
#     st.success("✅ すでにログイン済みです。")

# st.divider()

# # 📥 获取邮件与解析
# st.header("📥 メール取得・解析")

# col1, col2 = st.columns(2)

# with col1:
#     st.markdown("### ① GmailからSESメールを取得")
#     if st.button('メールを取る'):
#         if 'credentials' in st.session_state:
#             service = get_gmail_service()
#             progress_bar = st.progress(0)  # 进度条初始化
#             emails = fetch_ses_emails(service, progress_bar)  # 获取邮件
#             st.session_state['emails'] = emails
#             st.success(f"📨 メールの抽出が完了しました！共{len(emails)}件")
#         else:
#             st.error("⚠️ 先にログインしてください")

# with col2:
#     # st.markdown("### ② メール内容をGeminiで解析")
#     # if st.button('メール内容を抽出'):
#     #     if 'emails' not in st.session_state:
#     #         st.error("📭 メールを先に取得してください")
#     #     else:
#     #         emails = st.session_state['emails']
#     #         progress_bar = st.progress(0)
#     #         parser = GeminiParser()
#     #         email_data_list = []

#     #         for i, email in enumerate(emails, 1):
#     #             progress_bar.progress(i / len(emails))  # 更新进度条
#     #             parsed_data = parser.parse_email(email)  # 解析邮件
#     #             email_data_list.append(parsed_data)

#     #         st.session_state['email_data_list'] = email_data_list
#     #         st.success("🧠 Gemini解析が完了しました！")
#     st.markdown("### ② メール内容をGeminiで解析")
#     if st.button('メール内容を抽出'):
#         if 'emails' not in st.session_state:
#             st.error("先に『提取邮件』を実行してください")
#         else:
#             emails = st.session_state['emails']
#             progress_bar = st.progress(0)
#             parser = GeminiParser()
#             email_data_list = []

#             for i, email in enumerate(emails, 1):
#                     logging.info(f"\n--- メール {i}/{len(emails)} を処理中 ---")
#                     progress_bar.progress(i / len(emails)) 
                    
#                     # メタデータを抽出
#                     subject = extract_headers(email, 'Subject')
#                     sender = extract_headers(email, 'From')
#                     date = format_datetime(extract_headers(email, 'Date'))
#                     body_text = extract_body(email)

#                     logging.info(f"件名: {subject}")
#                     logging.info(f"送信者: {sender}")
#                     logging.info(f"日付: {date}")
                    
#                     if not body_text.strip():
#                         logging.warning("⚠️ 本文が空です。スキップします。")
#                         continue
                    
#                     # 内容を解析
#                     try:
#                         parsed = parser.parse_email(body_text)
#                         logging.info("解析結果:")
#                         logging.info(json.dumps(parsed, indent=2, ensure_ascii=False))
                        
#                         # データベース用のデータを準備
#                         email_data = {
#                             'received_at': date,
#                             'subject': subject,
#                             'sender_email': sender,
#                             'project_description': parsed.get('案件内容', ''),  # リストをカンマ区切りの文字列に変換
#                             # 'required_skills': ', '.join(parsed.get('必須スキル', [])),  # リストをカンマ区切りの文字列に変換
#                             # 'optional_skills': ', '.join(parsed.get('尚可スキル', [])),  # リストをカンマ区切りの文字列に変換
#                             'required_skills': parsed.get('必須スキル', []),
#                             'optional_skills': parsed.get('尚可スキル', []),
#                             "location": parsed.get("勤務地", ""),
#                             "unit_price": parsed.get("単価", ""),
#                             'message_id': email.get('id')  
#                         }
                        
#                         # 処理したデータを格納し、データベースに書き込む準備
#                         email_data_list.append(email_data)
                    
#                     except Exception as e:
#                         logging.error(f"❌ メールの処理中にエラーが発生しました: {str(e)}")
#             st.session_state['email_data_list'] = email_data_list
#             st.success("メールのフィルタリングが完了しました！")

# st.divider()

# # 💾 写入数据库
# st.header("💾 データベース保存")
# if st.button('データベースに書き込む'):
#     if 'email_data_list' not in st.session_state:
#         st.error("🔍 先にメール内容を抽出してください")
#     else:
#         email_data_list = st.session_state['email_data_list']
#         logging.info("📤 データベースに書き込みを開始します...")
#         for email_data in email_data_list:
#             insert_email_to_db(email_data)
#         st.success("✅ データベースへの保存が完了しました！")

# st.divider()

# # 📊 查看数据库内容
# st.header("📊 データベース内容の確認")
# df = get_db_data()
# if df.empty:
#     st.warning("📭 データがまだ登録されていません")
# else:
#     st.dataframe(df)

# st.divider()

# # 📤 导出到Google Sheets
# st.header("📤 Google Sheetsへのエクスポート")
# spreadsheet_id = st.text_input('📝 Google SheetsのスプレッドシートIDを入力してください')

# if st.button('Google Sheetsに書き込む'):
#     if spreadsheet_id:
#         if 'credentials' in st.session_state:
#             export_to_sheet(spreadsheet_id)
#             st.success("✅ Google Sheetsへの出力が完了しました")
#         else:
#             st.error("🔐 先にログインしてください")
#     else:
#         st.error("🆔 スプレッドシートIDを入力してください")






#直接sheettoに書き込む
import streamlit as st
import pandas as pd
import os
import json
import base64
import logging
import re
import pickle
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

# これらは4つのモジュールのインポート
from gmail.fetch_emails import fetch_ses_emails
from parser.gemini_parser import GeminiParser
from sheets.export_to_sheets_nomysql import export_to_sheet

import unicodedata
# Google認証に必要なスコープ
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/spreadsheets']

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def sanitize_text(text):
    if not isinstance(text, str):
        text = str(text)
    # 正規化して不可視文字を除去
    text = unicodedata.normalize('NFKC', text)
    # 絵文字や制御文字などを除去（必要なら）
    text = ''.join(c for c in text if unicodedata.category(c)[0] != "C")
    return text


def normalize_email_data(email_data_list):
    if isinstance(email_data_list, (dict, list)):  # 辞書またはリストの場合
        # まずJSON文字列に変換
        email_data_list = json.dumps(email_data_list)
    elif not isinstance(email_data_list, str):
        raise ValueError("提供的输入数据不是有效的字符串。")
    
    try:
        email_data_json = json.loads(email_data_list)
        return email_data_json
    except json.JSONDecodeError:
        raise ValueError("提供的字符串无法解析为有效的 JSON。")
    
def get_gspread_service():
    creds = None
    token_path = 'sheets/token_sheets.pickle'

    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('config/credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('sheets', 'v4', credentials=creds)

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
    

def export_to_sheet(email_data_list,spreadsheet_id, sheet_name="シート1"):
    if not email_data_list:
        print("📭 有効なメールデータが見つかりませんでした")
        return
    service = get_gspread_service()
    if isinstance(email_data_list, list):
        df = pd.DataFrame(email_data_list)
    else:
        # それ以外の型に対応する処理
        df = email_data_list  # 既にDataFrameの場合
    if df.empty:
        print("データベースにデータがありません。エクスポートを中止します。")
        return
    
    # 将列表转换为字符串（针对技能列）
    for col in ['required_skills', 'optional_skills']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)

    if 'unit_price' in df.columns:
        # 提取"万"单位的数值
        man_yen = df['unit_price'].str.extract(r'(\d+(?:\.\d+)?)\s*万').dropna()
        if not man_yen.empty:
            df.loc[man_yen.index, 'unit_price_numeric'] = man_yen[0].astype(float) * 10000
        
        # 提取普通数值
        normal_yen = df['unit_price'].str.extract(r'(\d+(?:,\d+)?)(?=円|$)').dropna()
        if not normal_yen.empty:
            df.loc[normal_yen.index, 'unit_price_numeric'] = normal_yen[0].str.replace(',', '').astype(float)

    if 'received_at' in df.columns:
        df['received_at'] = df['received_at'].astype(str)

    export_columns = [
        "message_id","received_at", "subject", "sender_email", "project_description",
        "required_skills", "optional_skills", "location", "unit_price" 
    ]
    existing_columns = [col for col in export_columns if col in df.columns]
    df_export = df[existing_columns].fillna('')

    # 英語→日本語の列名マッピング
    column_mapping = {
        "message_id": "メッセージID",
        "received_at": "受信日時",
        "subject": "件名",
        "sender_email": "送信者メール",
        "project_description": "案件内容",
        "required_skills": "必須スキル",
        "optional_skills": "尚可スキル",
        "location": "勤務地",
        "unit_price": "単価"
    }

    # 列ヘッダーを日本語に変換してデータ整形
    header = [column_mapping.get(col, col) for col in df_export.columns]
    data = [header] + [
    [sanitize_text(cell) for cell in row]
    for row in df_export.values.tolist()
]

    body = {'values': data}

    try:
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        print(f"✅ エクスポート完了、合計 {len(df_export)} 行をエクスポートしました。")
    except Exception as e:
        print(f"❌ スプレッドシートへのエクスポート中にエラーが発生しました: {str(e)}")



# def export_to_sheet(email_data_list, spreadsheet_id, sheet_name="シート1"):
#     """修正后的Google Sheets导出函数"""
#     # 1. 检查输入数据
#     if not email_data_list:
#         st.error("📭 没有找到有效邮件数据")
#         return
        
#     if 'credentials' not in st.session_state:
#         st.error("🔐 请先完成Google登录")
#         return

#     # 2. 数据预处理（与工作版本完全一致）
#     df = pd.DataFrame(email_data_list) if isinstance(email_data_list, list) else email_data_list
    
#     # 技能列转字符串
#     for col in ['required_skills', 'optional_skills']:
#         if col in df.columns:
#             df[col] = df[col].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
    
#     # 3. 准备导出数据
#     export_columns = [
#         "message_id", "received_at", "subject", "sender_email", 
#         "project_description", "required_skills", "optional_skills", 
#         "location", "unit_price"
#     ]
#     existing_columns = [col for col in export_columns if col in df.columns]
#     df_export = df[existing_columns].fillna('')

#     # 4. 列名中日文映射
#     column_mapping = {
#         "message_id": "メッセージID",
#         "received_at": "受信日時",
#         "subject": "件名",
#         # ...其他列映射保持与工作版本相同...
#     }
    
#     # 5. 构建写入数据
#     header = [column_mapping.get(col, col) for col in df_export.columns]
#     data = [header] + df_export.values.tolist()

#     # 6. 执行写入操作
#     try:
#         service = build('sheets', 'v4', credentials=st.session_state['credentials'])
        
#         # 先清空工作表
#         service.spreadsheets().values().clear(
#             spreadsheetId=spreadsheet_id,
#             range=sheet_name,
#             body={}
#         ).execute()

#         # 写入新数据
#         body = {'values': data}
#         result = service.spreadsheets().values().update(
#             spreadsheetId=spreadsheet_id,
#             range=sheet_name,
#             valueInputOption='RAW',
#             body=body
#         ).execute()
        
#         st.success(f"✅ 成功导出 {len(df_export)} 行数据")
#     except Exception as e:
#         st.error(f"❌ 导出失败: {str(e)}")

# Streamlit 页面配置
st.set_page_config(page_title="SES案件管理システム", layout="wide")

st.title('📩 SES案件管理システム')

st.markdown("これは **Gmail + Gemini + Google Sheets** を組み合わせたSES案件抽出ツールです。")

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
            st.error("先に『提取邮件』を実行してください")
        else:
            emails = st.session_state['emails']
            progress_bar = st.progress(0)
            parser = GeminiParser()
            email_data_list = []

            for i, email in enumerate(emails, 1):
                    logging.info(f"\n--- メール {i}/{len(emails)} を処理中 ---")
                    progress_bar.progress(i / len(emails)) 
                    
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
                        
                        # Google Sheetsに保存するためのデータを準備
                        email_data = {
                            'received_at': date,
                            'subject': subject,
                            'sender_email': sender,
                            'project_description': parsed.get('案件内容', ''),  # リストをカンマ区切りの文字列に変換
                            'required_skills': parsed.get('必須スキル', []),
                            'optional_skills': parsed.get('尚可スキル', []),
                            "location": parsed.get("勤務地", ""),
                            "unit_price": parsed.get("単価", ""),
                            'message_id': email.get('id')  
                        }
                        
                        # 処理したデータを格納
                        email_data_list.append(email_data)
                    
                    except Exception as e:
                        logging.error(f"❌ メールの処理中にエラーが発生しました: {str(e)}")
            st.session_state['email_data_list'] = email_data_list
            st.success("メールのフィルタリングが完了しました！")

st.divider()

# # 📤 导出到Google Sheets
# st.header("📤 Google Sheetsへのエクスポート")
# spreadsheet_id = st.text_input('📝 Google SheetsのスプレッドシートIDを入力してください')
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
if st.button('Google Sheetsに書き込む'):
    if SPREADSHEET_ID:
        export_to_sheet(
            email_data_list=st.session_state.get('email_data_list', []),
            spreadsheet_id=SPREADSHEET_ID,
            sheet_name="シート1"  # 保持与工作版本相同的表名
        )
    else:
        st.error("🆔 スプレッドシートIDを入力してください")
