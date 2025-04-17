from gmail.fetch_emails import get_gmail_service, fetch_ses_emails
from parser.gemma_parser import GemmaParser
from db.db_writer import insert_email_to_db
import base64
import json
from datetime import datetime

def extract_headers(msg, name):
    """メールヘッダーから特定のフィールドを抽出"""
    headers = msg.get('payload', {}).get('headers', [])
    for h in headers:
        if h.get('name', '').lower() == name.lower():
            return h.get('value', '')
    return ''

def extract_body(msg) -> str:
    """Gmailメッセージからプレーンテキストの本文を抽出"""
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
    """Gmailの日付文字列をMySQL形式にフォーマット"""
    try:
        return datetime.strptime(gmail_date, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M:%S')
    except:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def main():
    print("🔍 Gmailからメールを取得中...")
    service = get_gmail_service()  # Gmailサービスを取得
    emails = fetch_ses_emails(service)  # SESメールを取得

    if not emails:
        print("📭 今日のメールが見つかりません")
        return

    print(f"\n📩 {len(emails)} 通のメールが見つかりました")
    parser = GemmaParser()  # GemmaParserのインスタンスを作成

    for i, email in enumerate(emails, 1):
        print(f"\n--- メール {i}/{len(emails)} を処理中 ---")
        
        # メールのメタデータを抽出
        subject = extract_headers(email, 'Subject')  # 件名を抽出
        sender = extract_headers(email, 'From')  # 送信者を抽出
        date = format_datetime(extract_headers(email, 'Date'))  # 日付をフォーマット
        body_text = extract_body(email)  # 本文を抽出

        print(f"件名: {subject}")
        print(f"送信者: {sender}")
        print(f"日付: {date}")
        
        if not body_text.strip():
            print("⚠️ 本文が空です。スキップします。")
            continue
        
        # メール内容を解析
        try:
            parsed = parser.parse_email(body_text)  # GemmaParserで解析
            print("解析結果:")
            print(json.dumps(parsed, indent=2, ensure_ascii=False))  # 解析結果を表示
            
            # データベース用のデータを準備
            email_data = {
                'received_at': date,
                'subject': subject,
                'sender_email': sender,
                'project_description': parsed.get('案件内容', ''),
                'required_skills': parsed.get('必須スキル', []),
                'optional_skills': parsed.get('尚可スキル', []),
                'location': parsed.get('勤務地', ''),
                'unit_price': parsed.get('単価', '')
            }
            
            # データベースに保存
            insert_email_to_db(email_data)
            print("✅ データベースに保存しました")
            
        except Exception as e:
            print(f"❌ メール処理に失敗しました: {str(e)}")

if __name__ == "__main__":
    main()
