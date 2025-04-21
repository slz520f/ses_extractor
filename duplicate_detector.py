import mysql.connector
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import Levenshtein
from dotenv import load_dotenv
from collections import defaultdict
from test.export_to_sheets_test import export_duplicates_to_sheet


load_dotenv()
MYSQL_HOST =os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")

def get_db_connection():
    if not all([MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE]):
        print("Database credentials are not set in the environment variables.")
        return None
    try:
        print("データベースに接続中...")
        conn=mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        #接続成功時にカーソルを作成
        print("データベースに接続しました。")
        
        return conn
    except    mysql.connector.Error as err:
        print(f"データベース接続失敗: {err}")
        return None

def fetch_all_projects():
    conn=get_db_connection()
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT message_id, subject, project_description, required_skills, unit_price FROM ses_projects")
        return cursor.fetchall()
    
def is_similar(a,b,threshold=0.75):
    desc_similarity=Levenshtein.ratio(a["project_description"],b["project_description"])
    skills_similarity=Levenshtein.ratio(a["required_skills"],b["required_skills"])
    unit_similarity=1 if a["unit_price"]==b["unit_price"] else 0

    total_similartiy=(desc_similarity*0.5 + skills_similarity*0.3 + unit_similarity*0.2)
    return total_similartiy>=threshold   

def group_similar_projects(projects):
    visited = set()
    groups = []
    for i,proj in enumerate(projects):
        if proj["message_id"] in visited:
            continue
        group=[proj]
        visited.add(proj["message_id"])
        for j in range(i+1,len(projects)):
            other =projects[j]
            if other["message_id"] not in visited and is_similar(proj,other):
                group.append(other)
                visited.add(other["message_id"])

        if len(group)>1:
            groups.append(group)
    return groups

def main():
    print("🚀 重複案件検出 開始...")
    projects = fetch_all_projects()
    similar_groups = group_similar_projects(projects)

    if not similar_groups:
        print("✅ 類似案件なし")
        return

    SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
    export_duplicates_to_sheet(similar_groups, SPREADSHEET_ID)

if __name__ == "__main__":
    main()
