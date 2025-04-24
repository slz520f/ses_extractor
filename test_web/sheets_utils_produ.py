import pandas as pd
import unicodedata
import json
import os
import pickle
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import secrets  #


SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/spreadsheets']
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
    token_path = '/tmp/token_sheets.pickle'
    
    # 检查并删除可能无效的旧令牌
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        except (RefreshError, pickle.UnpicklingError) as e:
            os.unlink(token_path)  # 删除无效的令牌文件
            creds = None
            st.warning("セッションが期限切れです。再度ログインしてください。")

    if not creds or not creds.valid:
        oauth_secrets = st.secrets["google_oauth"]
        redirect_uri = oauth_secrets["redirect_uris"][0]  # 确保使用第一个重定向URI

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": oauth_secrets["client_id"],
                    "client_secret": oauth_secrets["client_secret"],
                    "auth_uri": oauth_secrets["auth_uri"],
                    "token_uri": oauth_secrets["token_uri"],
                    "auth_provider_x509_cert_url": oauth_secrets["auth_provider_x509_cert_url"],
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )

        if 'code' not in st.query_params:
            # 添加state参数防止CSRF攻击
            state = secrets.token_urlsafe(16)
            st.session_state['oauth_state'] = state
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                prompt='consent',
                state=state,
                include_granted_scopes='true'
            )
            st.markdown(f"[👉 Googleで再ログイン]({auth_url})")
            st.stop()
        else:
            try:
                # 验证state参数防止CSRF攻击
                if st.query_params.get('state') != st.session_state.get('oauth_state'):
                    st.error("セキュリティ検証に失敗しました。再度お試しください。")
                    st.stop()
                
                flow.fetch_token(code=st.query_params["code"])
                creds = flow.credentials
                
                # 保存新令牌
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                    
                # 清除code参数防止重复使用
                st.query_params.clear()
                
            except Exception as e:
                st.error(f"認証失敗: {str(e)}")
                if 'credentials' in st.session_state:
                    del st.session_state['credentials']
                st.stop()

    return build('sheets', 'v4', credentials=creds)

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




