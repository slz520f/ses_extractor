🧩 使用技術
フロントエンド：Next.js（App Router）+ TypeScript + Chakra UI

バックエンド：FastAPI

データベース：Supabase（PostgreSQL）

タスクスケジューラー：APScheduler

認証：Google OAuth 2.0

デプロイ：Render

🔗 公開URL

種別	URL
フロントエンド	https://ses-extractor-1.onrender.com
バックエンド	https://ses-extractor.onrender.com
🚀 主な機能
🔐 Googleアカウントでログイン（OAuth 2.0）

📩 Gmailから「SES」「案件」「求人」などのキーワードを含むメールを自動取得

🧠 メール本文から以下の情報を抽出：

件名、発信者、勤務地、単価、必須スキル、尚可スキルなど

🗃️ Supabaseに保存（プロジェクト一覧として管理）

⏱️ APSchedulerで毎時自動取得

🧾 フロントエンドで一覧表示、解析状況などを確認可能

📦 ローカルでの実行方法
1. リポジトリのクローン
bash
コピーする
編集する
git clone https://github.com/yourusername/ses-extractor.git
cd ses-extractor
2. 環境変数の設定
フロントエンド .env.local
env
コピーする
編集する
NEXT_PUBLIC_API_BASE_URL=https://ses-extractor.onrender.com
NEXT_PUBLIC_GOOGLE_CLIENT_ID=あなたのGoogleClientID
NEXT_PUBLIC_GOOGLE_REDIRECT_URI=https://ses-extractor-1.onrender.com/api/auth/callback/google
バックエンド .env
env
コピーする
編集する
SUPABASE_URL=あなたのSupabaseのURL
SUPABASE_SERVICE_ROLE_KEY=Supabaseのサービスロールキー
GOOGLE_CLIENT_ID=あなたのGoogleクライアントID
GOOGLE_CLIENT_SECRET=あなたのGoogleクライアントシークレット
3. バックエンドの起動（FastAPI）
bash
コピーする
編集する
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
4. フロントエンドの起動（Next.js）
bash
コピーする
編集する
cd frontend
npm install
npm run dev
🛠️ データベース構成（Supabase）
テーブル：ses_projects

カラム名	型	内容
id	UUID	主キー
received_at	timestamp	メール受信日時
subject	text	メール件名
sender_email	text	差出人メールアドレス
project_description	text	メール本文
required_skills	text	必須スキル
optional_skills	text	尚可スキル
location	text	勤務地
unit_price	text	単価
message_id	text	GmailメッセージID
is_parsed	boolean	解析済みフラグ
processed	boolean	処理済みフラグ
created_at	timestamp	作成日時（自動生成）
⏱️ 自動処理の流れ
APSchedulerが1時間ごとに実行

OAuthトークンでGmail APIにアクセス

「案件 OR SE OR 求人」＋未ラベルのメールを取得

解析対象メールを抽出（添付ファイルのないメール）

Supabaseへ保存・解析


# データベース構造 (Database Schema)

## ER図 (Entity Relationship Diagram)

```mermaid
erDiagram
    raw_emails ||--o{ ses_projects : "1:N"
    raw_emails {
        int id PK "ID (主キー)"
        varchar message_id "メールID / Message ID"
        jsonb raw_data "生データ / Raw email content"
        timestamptz created_at "作成日時 / Created time"
    }
    
    ses_projects {
        int id PK "ID (主キー)"
        int raw_email_id FK "生メールID / Raw email FK"
        timestamp received_at "受信日時 / Received time"
        text subject "件名 / Subject"
        varchar sender_email "送信者メール / Sender email"
        text project_description "案件内容 / Project description"
        text required_skills "必須スキル / Required skills"
        text optional_skills "尚可スキル / Optional skills"
        text location "勤務地 / Location"
        varchar unit_price "単価 / Unit price"
        varchar message_id "メールID / Message ID"
        timestamp created_at "作成日時 / Created time"
        boolean is_parsed "解析済み / Is parsed"
        int project_index "案件番号 / Project index"
    }

    user_tokens {
        uuid id PK "ID (主キー)"
        text user_email "ユーザーメール / User email"
        text access_token "アクセストークン / Access token"
        text refresh_token "リフレッシュトークン / Refresh token"
        timestamptz expires_at "有効期限 / Expiration time"
        timestamptz created_at "作成日時 / Created time"
        timestamptz updated_at "更新日時 / Updated time"
    }

    %% ビュー (View)
    project_with_raw_data }|..|| raw_emails : "クエリ依存 / Query dependency"
    project_with_raw_data }|..|| ses_projects : "クエリ依存 / Query dependency"
    
    note for project_with_raw_data "仮想ビュー / Virtual View\n\n結合内容 / Combines:\n- ses_projects全項目\n- raw_emails.raw_data\n\n用途 / Purpose:\n1. 案件+生メール統合表示\n   Unified project & raw email view\n2. フロントエンド簡素化\n   Frontend query simplification"
```

## 主要関係説明 (Key Relationships)

| 関係 | 説明 (日本語) | Description (English) |
|------|---------------|-----------------------|
| raw_emails → ses_projects | 1件の生メールから複数案件が生成可能 | One raw email can generate multiple projects |
| project_with_raw_data | 案件データと生メール内容を結合したビュー | View combining projects with raw email data |

## ビュー定義例 (View Definition Example)

```sql
CREATE VIEW project_with_raw_data AS
SELECT 
  sp.*,
  re.raw_data
FROM 
  ses_projects sp
JOIN 
  raw_emails re ON sp.raw_email_id = re.id;
```

## インデックス推奨 (Recommended Indexes)

```sql
-- パフォーマンス最適化のため
CREATE INDEX idx_ses_projects_raw_email ON ses_projects(raw_email_id);
CREATE INDEX idx_raw_emails_message_id ON raw_emails(message_id);
```

## 注意事項 (Notes)
1. ビューは仮想テーブルで物理的にデータを保持しません  
   (Views are virtual tables without physical storage)
2. `raw_data` フィールドにはBase64エンコードされた本文が含まれる場合があります  
   (May contain Base64-encoded content)



