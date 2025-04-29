import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量中获取 Supabase 的 URL 和密钥
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 创建 Supabase 客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_project_data(project_data):
    # 插入数据到 ses_projects 表
    response = supabase.table("ses_projects").insert(project_data).execute()
    return response

# 你的邮件数据
project_data = {
    "received_at": "2025-04-25 10:00:00",  # 示例：邮件接收时间
    "subject": "New SES Project",  # 示例：邮件主题
    "sender_email": "example@domain.com",  # 示例：发件人邮箱
    "project_description": "This is a description of the SES project.",  # 示例：项目描述
    "required_skills": "Python, Machine Learning",  # 示例：必需的技能
    "optional_skills": "Flask, FastAPI",  # 示例：可选技能
    "location": "Tokyo, Japan",  # 示例：位置
    "unit_price": "100,000 JPY",  # 示例：单价
    "message_id": "unique-message-id-12345"  # 示例：消息ID
}

# 调用函数插入数据
response = insert_project_data(project_data)

# 输出返回结果
print(response)
