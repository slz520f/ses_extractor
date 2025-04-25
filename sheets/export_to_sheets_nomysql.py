



import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from gmail.fetch_emails import get_gmail_service, fetch_ses_emails
from parser.gemini_parser import GeminiParser
import logging
from datetime import datetime
import base64
import re
import json



# 環境変数の読み込み
load_dotenv()

# スプレッドシートのスコープ
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


import unicodedata

# セル内のテキストをクリーンアップする関数
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


# -------------------------
# Google Sheetsの認証
# -------------------------
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

# 単価の文字列を数値に変換する関数
def clean_unit_price(price_str):
    # 如果是 Series 直接返回 None
    if isinstance(price_str, pd.Series):
        return None
    
    if pd.isna(price_str) or price_str == '':
        return None
        
    if isinstance(price_str, (int, float)):
        return float(price_str)
        
    # 处理字符串
    price_str = str(price_str)
    match = re.search(r'(\d+(?:,\d+)?)(?=円|$)', price_str)
    if match:
        return float(match.group(1).replace(',', ''))
    match_man = re.search(r'(\d+(?:\.\d+)?)\s*万', price_str)
    if match_man:
        return float(match_man.group(1)) * 10000
    return None
# -------------------------
# スプレッドシートへのエクスポート
# -------------------------
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


# -------------------------
# ヘッダー・本文 抽出ユーティリティ
# -------------------------
def extract_headers(msg, name):
    headers = msg.get('payload', {}).get('headers', [])
    for h in headers:
        if h.get('name', '').lower() == name.lower():
            return h.get('value', '')
    return ''


def extract_body(msg) -> str:
    payload = msg.get('payload', {})
    parts = payload.get('parts', [])
    for part in parts:
        if part.get('mimeType') == 'text/plain':
            data = part.get('body', {}).get('data', '')
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')

    if 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

    return msg.get('snippet', '')


def format_datetime(gmail_date):
    try:
        gmail_date = re.sub(r'\s*\(.*\)$', '', gmail_date)
        return datetime.strptime(gmail_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.error(f"日付のフォーマットに失敗しました: {str(e)}")
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# -------------------------
# メイン処理
# -------------------------
def main():
    logging.info("🔍 Gmailからメールを取得中...")
    email_data_list = []

    try:
        service = get_gmail_service()
        emails = fetch_ses_emails(service)

        if not emails:
            logging.warning("📭 今日のメールは見つかりませんでした")
            return []

        logging.info(f"\n📩 {len(emails)} 件の該当するメールが見つかりました")

        parser = GeminiParser()

        for i, email in enumerate(emails, 1):
            logging.info(f"\n--- メール {i}/{len(emails)} を処理中 ---")

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

            try:
                parsed = parser.parse_email(body_text)
                logging.info("解析結果:")
                logging.info(json.dumps(parsed, indent=2, ensure_ascii=False))

                email_data = {
                    'received_at': date,
                    'subject': subject,
                    'sender_email': sender,
                    'project_description': parsed.get('案件内容', ''),
                    'required_skills': parsed.get('必須スキル', []),
                    'optional_skills': parsed.get('尚可スキル', []),
                    "location": parsed.get("勤務地", ""),
                    "unit_price": parsed.get("単価", ""),
                    'message_id': email.get('id')
                }

                email_data_list.append(email_data)

            except Exception as e:
                logging.error(f"❌ メール処理中にエラーが発生しました: {str(e)}")

    except Exception as e:
        logging.error(f"メインプログラム実行中にエラーが発生しました: {str(e)}")

    return email_data_list


# -------------------------
# 実行ブロック
# -------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    email_data_list = main()

    if email_data_list:
       
        export_to_sheet(email_data_list, SPREADSHEET_ID,sheet_name="シート1")
    else:
        print("📭 有効なメールデータが見つかりませんでした")
