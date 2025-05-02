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

