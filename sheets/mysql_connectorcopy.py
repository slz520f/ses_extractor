# db/mysql_connector.py
import mysql.connector
from mysql.connector import Error
import yaml
import os

def load_db_config():
    with open(os.path.join('config', 'settings.yaml'), 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config.get('mysql')

def get_connection():
    config = load_db_config()
    try:
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        return connection
    except Error as e:
        print("数据库连接失败", e)
        return None

def insert_project(data):
    """
    data 为字典，包含：
      received_at, subject, sender_email, raw_body,
      project_description, required_skills, optional_skills,
      location, unit_price
    """
    conn = get_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    insert_query = """
    INSERT INTO ses_projects 
    (received_at, subject, sender_email, raw_body, project_description,
     required_skills, optional_skills, location, unit_price)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (
        data.get('received_at'),
        data.get('subject'),
        data.get('sender_email'),
        data.get('raw_body'),
        data.get('project_description'),
        data.get('required_skills'),
        data.get('optional_skills'),
        data.get('location'),
        data.get('unit_price')
    )
    try:
        cursor.execute(insert_query, values)
        conn.commit()
        return True
    except Error as e:
        print("数据写入失败：", e)
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # 测试用数据，确保 settings.yaml 中配置正确
    sample_data = {
        "received_at": "2023-12-01 10:00:00",
        "subject": "テスト案件",
        "sender_email": "test@example.com",
        "raw_body": "案件内容：XXプロジェクト...",
        "project_description": "XXプロジェクトの詳細",
        "required_skills": "Python, SQL",
        "optional_skills": "GCP",
        "location": "東京都",
        "unit_price": "500000円"
    }
    success = insert_project(sample_data)
    print("写入成功" if success else "写入失败")
