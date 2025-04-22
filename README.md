# ses_extractor
# SES案件マネジメントシステム
#エンジニア向け
    ## 🚀 概要
    GmailのSES案件メールを自動処理し、検索可能なデータベース化するシステム。AIによる情報抽出とGoogleスプレッドシート連携機能を備える。

    ## ✅ 動作環境
    - Python 3.10+
    - MySQL 8.0+
    - Google Cloud Platformアカウント

    ## ⚙️ セットアップ手順
    1. Visual Studio Code インストール
    Windows:

    - [VS Code公式サイト](https://code.visualstudio.com/) にアクセス 
    「Download for Windows」ボタンをクリック
    ダウンロードした VSCodeUserSetup-x64-*.exe をダブルクリック
    インストールオプション：
    「PATHへの追加」にチェック ✓
    「ファイルコンテキストメニューに開くを追加」にチェック ✓

    Mac:

    \```bash
    # Homebrew経由でインストール（推奨）
    brew install --cask visual-studio-code
    \```
    # または手動で：
    # 1. 公式サイトから .dmg ファイルをダウンロード
    # 2. ダウンロードフォルダでダブルクリック
    # 3. アプリケーションフォルダにドラッグ&ドロップ

    2. Python インストール
    Windows:

    - [Python公式サイト](https://www.python.org/) へアクセス  
    「Download Python 3.10.x」をクリック
    インストーラー実行時：
    「Add Python to PATH」に必ずチェック ✓
    「Install launcher for all users」もチェック ✓
    コマンドプロンプトで確認：
    \```bash
    python --version
    > Python 3.10.X
    \```

    Mac:

    \```bash
    # Homebrew経由
    brew install python@3.10

    # パスを通す
    echo 'export PATH="/usr/local/opt/python@3.10/bin:$PATH"' >> ~/.zshrc
    source ~/.zshrc

    # 確認
    python3 --version
    > Python 3.10.X
    \```

    3. MySQL インストール詳細

    Windows:

    [MySQL Installerダウンロード](https://dev.mysql.com/downloads/installer/)
    インストーラー実行：
    Setup Type: Custom を選択
    Products: MySQL Server 8.0.X と MySQL Workbench を追加
    Authentication Method: Use Legacy Authentication Method を選択
    パスワード設定画面：
    Root Password: 
    Windows Service: Configure MySQL Server as a Windows Service をチェック

    Mac:

    \```bash
    # MySQLサーバーインストール
    brew install mysql

    # 自動起動設定（再起動後も有効）
    brew services start mysql

    # セキュリティ設定
    mysql_secure_installation
    # 質問には全てYで回答

    # パスワード設定
    mysql -u root -p
    ALTER USER 'root'@'localhost' IDENTIFIED BY '自分が設定したいパスワード';
    FLUSH PRIVILEGES;
    exit
    \```

    4.上記なセットアップ終了後VScodeを開く、timelineを開く、以下のコードを書く。
        \```bash
        # 1. リポジトリクローン
        git clone https://github.com/slz520f/ses_extractor.git

        # 2. 仮想環境作成
        python -m venv venv
        source venv/bin/activate  # Linux/Mac
        venv\Scripts\activate    # Windows

        # 3. 依存関係インストール
        pip install -r requirements.txt

        # 4. 設定ファイル準備
        \```
        （GCP/Gmail APIの認証情報を入力）
            # 4.1 .envファイル準備（秘密情報用）
                # Gemini 2.0 Flash-Lite API
                API_KEY=**********

                # MySqlの設定(DATABASE名はses_db,TABLE名はses_projects,ses_projectsの内容はdb/schema.sqlに参照)
                MYSQL_HOST=localhost # 自分がdatabase作る時選択できる
                MYSQL_USER=root #自分がdatabase作る時選択できる
                MYSQL_PASSWORD=********** #自分がdatabase作る時設定したパスワード
                MYSQL_DATABASE=ses_db #今のコード使うならses_dbにしてください

                # 自分のスプレットシートのID,
                # 例https://docs.google.com/spreadsheets/d/**********/edit?hl=ja&gid=0#gid=0     ==>****の部分はID
                SPREADSHEET_ID=**********

                GOOGLE_API_KEY=**********
                GOOGLE_SHEET_CREDENTIAL=**********
            # 4.2 config/ファイル準備
                Google API認証情報取得手順
                
                Google Cloud Console設定
                    ⭕️[Google Cloud Console](https://console.cloud.google.com/) にログイン
                    ⭕️画面上部のプロジェクト選択 → 「新しいプロジェクト」作成
                        プロジェクト名：SES-Management
                        ロケーション：組織なし

                API有効化
                    ⭕️ナビゲーションメニュー → 「APIとサービス」→「ライブラリ」
                    ⭕️以下を検索して有効化：
                        Gmail API
                        Google Sheets API

                OAuth同意画面設定
                    ⭕️「OAuth同意画面」→「外部」→「作成」
                        アプリ情報：
                            アプリ名：SES Management System
                            ユーザーサポートメール：自分のアドレス
                    ⭕️データアクセス→コップ追加：.../auth/gmail.readonly, .../auth/spreadsheets

                認証情報作成
                    ⭕️「クライアント」→「OAuth クライアントID」
                    ⭕️アプリケーション種類：デスクトップアプリ
                    ⭕️名前：Desktop-client
                    ⭕️「作成」後、JSONをダウンロード → config/credentials.json に保存    
        # 5.python main.py実行



#一般ユーザー向け：アプリの使い方
        #1. 事前準備
            config/credentials.json をアプリと同じ場所に置く

            .env ファイルを作成し、以下を記載（メモ帳で編集OK）

            env
            API_KEY=**********
            MYSQL_HOST=localhost
            MYSQL_USER=root
            MYSQL_PASSWORD=**********
            MYSQL_DATABASE=ses_db
            SPREADSHEET_ID=**********
            GOOGLE_API_KEY=**********
            GOOGLE_SHEET_CREDENTIAL=**********
        #2. launcher をダブルクリックして実行
            初回起動時、ブラウザが自動で開き、Streamlit アプリが開始されます。

            ブラウザ上の操作だけで、メール抽出・AI解析・DB保存・Sheets出力ができます。

        📁 配布パッケージ構成
            
            ses_extractor_app/
            │
            ├─ dist/
            │   └─ launcher  (実行ファィル)
            ├─ config/
            │   └─ credentials.json
            ├─ .env
            ├─ README.txt（簡易マニュアル）