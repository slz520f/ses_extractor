


import sys
import os
import pandas as pd
import mysql.connector
from dotenv import load_dotenv

# パス追加（parserモジュールを読み込むため）
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from parser.gemma_parser_xlsx import GemmaParser

# .envを読み込む
load_dotenv()

# 環境変数からMySQL接続情報を取得
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

# DB接続関数
def get_db_connection():
    if not all([MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE]):
        print("❌ MySQLの設定が不足しています。")
        return None, None
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        print("✅ データベース接続成功")
        return conn, conn.cursor()
    except mysql.connector.Error as err:
        print(f"❌ データベース接続失敗: {err}")
        return None, None

# Excel読み込み
df = pd.read_excel("ダミー案件20件.xlsx")  # ファイル名は必要に応じて調整
parser = GemmaParser()  # パーサー初期化

# DB接続
conn, cursor = get_db_connection()
if not conn:
    sys.exit(1)

# 各行処理
for idx, row in df.iterrows():
    email_text = row.get("本文", "")
    received_at = row.get("受信日時", None)
    subject = row.get("件名", "")
    sender_email = row.get("送信者アドレス", "")
    
    parsed = parser.parse_email(email_text)

    insert_query = """
        INSERT INTO ses_projects (
            received_at, subject, sender_email, 
            project_description, required_skills, optional_skills, location,
            unit_price
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    data = (
        received_at,
        subject,
        sender_email,
        parsed.get("案件内容", ""),
        ', '.join(parsed.get("必須スキル", [])),
        ', '.join(parsed.get("尚可スキル", [])),
        parsed.get("勤務地", ""),
        parsed.get("単価", "")
    )
    
    try:
        cursor.execute(insert_query, data)
    except Exception as e:
        print(f"❌ データ挿入エラー（{idx}行目）: {e}")
        continue

# コミット & 終了処理
conn.commit()
cursor.close()
conn.close()
print("✅ MySQLへの保存完了！")
