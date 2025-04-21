


import pandas as pd
import mysql.connector
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle
import os
import re
from dotenv import load_dotenv

# 環境変数を読み込む
load_dotenv()

# Google Sheets APIで使用するスコープ
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Google Sheetsの認証サービスを取得する関数
def get_gspread_service():
    creds = None
    token_path = 'sheets/token_sheets.pickle'

    # 認証トークンが既に存在する場合は読み込み
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # トークンが無効な場合、新しく認証フローを実行
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('config/credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    return build('sheets', 'v4', credentials=creds)

# MySQLからデータを取得する関数
def get_db_data():
    try:
        # 環境変数からDB接続情報を取得
        host = os.getenv("MYSQL_HOST")
        user = os.getenv("MYSQL_USER")
        password = os.getenv("MYSQL_PASSWORD")
        database = os.getenv("MYSQL_DATABASE")

        # MySQLへ接続
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )

        # データをpandasのDataFrameで取得
        df = pd.read_sql("SELECT * FROM ses_projects", conn)
        conn.close()
        return df

    except mysql.connector.Error as e:
        print("データベースの読み取りに失敗しました：", e)
        return pd.DataFrame()

# 単価の文字列を数値に変換する関数
def clean_unit_price(price_str):
    if pd.isna(price_str):
        return None
    match = re.search(r'(\d+(?:,\d+)?)(?=円|$)', price_str)
    if match:
        return float(match.group(1).replace(',', ''))
    match_man = re.search(r'(\d+(?:\.\d+)?)\s*万', price_str)
    if match_man:
        return float(match_man.group(1)) * 10000
    return None

# Google Sheets にデータを書き込む関数
def export_to_sheet(spreadsheet_id, sheet_name="シート1"):
    service = get_gspread_service()
    df = get_db_data()

    if df.empty:
        print("データベースにデータがありません。エクスポートを中止します。")
        return

    df['unit_price_numeric'] = df['unit_price'].apply(clean_unit_price)
    df.sort_values(by='unit_price_numeric', ascending=True, inplace=True, na_position='last')

    if 'received_at' in df.columns:
        df['received_at'] = df['received_at'].astype(str)

    export_columns = [
        "message_id","received_at", "subject", "sender_email", "project_description",
        "required_skills", "optional_skills", "location", "unit_price" 
    ]
    df_export = df[export_columns].fillna('')

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
    data = [header] + df_export.values.tolist()

    body = {'values': data}

    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=sheet_name,
        valueInputOption='RAW',
        body=body
    ).execute()

    print(f"✅ エクスポート完了、合計 {len(df_export)} 行をエクスポートしました。")

# メイン処理
if __name__ == "__main__":
    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    export_to_sheet(SPREADSHEET_ID)
