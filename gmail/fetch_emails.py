import os
import pickle
import base64
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Gmail APIのスコープ（読み取り専用）
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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
            flow = InstalledAppFlow.from_client_secrets_file('config/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # トークンを保存
        with open('gmail/token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    # Gmail APIサービスをビルドして返す
    service = build('gmail', 'v1', credentials=creds)
    return service

def get_today_date_query():
    """当日限定の検索クエリを作成する関数"""
    today = datetime.now()
    tomorrow = today + timedelta(days=1)

    after_str = today.strftime('%Y/%m/%d')
    before_str = tomorrow.strftime('%Y/%m/%d')

    return f'after:{after_str} before:{before_str}'

def fetch_ses_emails(service, query="(案件 OR SE OR 求人   ) has:nouserlabels "):
    """当日受信したSES案件メール（添付ファイルなし）を取得"""
    date_query = get_today_date_query()
    full_query = f" {query}{date_query}"
    
    print(f"実行クエリ: {full_query}")
    
    # メールメッセージ一覧を取得
    results = service.users().messages().list(
        userId='me', 
        q=full_query, 
        maxResults=2000  # 最大2000件
    ).execute()
    
    messages = results.get('messages', [])
    ses_emails = []
    
    for msg_meta in messages:
        # 各メッセージの詳細を取得
        msg = service.users().messages().get(
            userId='me', 
            id=msg_meta['id'], 
            format='full'
        ).execute()
        
        # 添付ファイルがあるかチェック
        parts = msg.get('payload', {}).get('parts', [])
        has_attachment = any(
            part.get('filename') and part['filename'] != '' 
            for part in parts
        )
        
        # 添付ファイルなしのメールのみ追加
        if not has_attachment:
            ses_emails.append(msg)
    
    return ses_emails

# メイン処理
if __name__ == "__main__":
    try:
        # Gmailサービスを取得
        service = get_gmail_service()
        # SES案件メールを取得
        emails = fetch_ses_emails(service)
        print(f"【結果】当日のSES案件メール: {len(emails)}件")
        
#         # 件名をデバッグ表示（必要に応じて使用）
#         for i, email in enumerate(emails[:3], 1):
#             headers = email['payload']['headers']
#             subject = next(
#                 (h['value'] for h in headers if h['name'] == 'Subject'), 
#                 '件名なし'
#             )
#             print(f"\nサンプル{i}: {subject}")
            
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
