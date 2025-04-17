

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import re 
from utils.price_simplifier import PriceSimplifier
import mysql.connector


from dotenv import load_dotenv  # 导入 dotenv
from utils.price_simplifier import PriceSimplifier

# .envファイルを読み込む
load_dotenv()

# .envからMySQL設定を取得
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

def get_db_connection():
    if not all([MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE]):
        print("MySQLの設定が不足しています。確認してください。")
        return None, None
    
    try:
        # MySQLに接続
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        
        # 接続成功時にカーソルを作成
        print("データベース接続成功")
        cursor = conn.cursor()
        return conn, cursor
    except mysql.connector.Error as err:
        print(f"データベース接続失敗: {err}")
        return None, None
    except Exception as e:
        print(f"設定読み込み失敗: {e}")
        return None, None

def insert_email_to_db(email_data):
    conn, cursor = get_db_connection()
    
    # データベース接続に失敗した場合、処理を中止する
    if conn is None or cursor is None:
        print("データベース接続に失敗しました。処理を中止します。")
        return
    
    try:
        # PriceSimplifierのインスタンス作成
        price_simplifier = PriceSimplifier()

        # 単価を簡略化
        simplified_price = price_simplifier.simplify_price(email_data.get('unit_price', ''))

        # データ挿入用SQLクエリ
        insert_query = """
            INSERT INTO ses_projects (
                received_at, subject, sender_email, 
                project_description, required_skills, optional_skills, location,
                unit_price
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        # データの準備
        data = (
            email_data['received_at'],
            email_data['subject'],
            email_data['sender_email'],
            email_data['project_description'],
            ', '.join(email_data['required_skills']),
            ', '.join(email_data['optional_skills']),
            email_data['location'],
            simplified_price  # 簡略化された単価
        )
        
        # SQLクエリを実行
        cursor.execute(insert_query, data)
        
        # トランザクションをコミット
        conn.commit()
        
        print(f"{cursor.rowcount} 行のデータを正常に挿入しました。")

    except mysql.connector.Error as err:
        print(f"データベースエラー: {err}")
    finally:
        # 接続を閉じる
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# テスト用データ
# email_data = {
#     'received_at': '2025-04-16 12:34:56',
#     'subject': '案件タイトル',
#     'sender_email': 'example@example.com',
#     'raw_body': 'メール本文...',
#     'project_description': '案件詳細...',
#     'required_skills': ['Java', 'SQL'],
#     'optional_skills': ['Docker'],
#     'location': '東京都',
#     'unit_price': '¥500,000/月'
# }

# insert_email_to_db(email_data)