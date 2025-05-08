import json
from datetime import datetime
from gemini_and_db import GeminiParser, send_to_api, save_raw_email
import os
from dotenv import load_dotenv
import base64

# 加载环境变量
load_dotenv()

def create_test_email():
    """创建符合标准结构的测试邮件数据"""
    with open('ses_extractor_bakcend/real_email.txt', 'r', encoding='utf-8') as f:
        email_content = f.read()
    
    # 构造符合后端处理逻辑的标准数据结构
    test_email = {
        "id": "real_email_001",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "PrimeVideoの吹替制作スタッフなど！人気の求人をお送りします。"},
                {"name": "From", "value": '"エンゲージ事務局" <info@engage.en-japan.com>'},
                {"name": "Date", "value": "Thu, 2 May 2025 14:25:45 +0900"}
            ],
            "body": {
                "data": base64.b64encode(email_content.encode('utf-8')).decode('utf-8')
            }
        }
    }
    
    # 转换为JSON字符串模拟数据库存储
    return json.dumps(test_email, ensure_ascii=False)

def test_hard_case():
    
    
    # 创建测试邮件
    raw_email_json = create_test_email()
    print("生成的测试邮件JSON结构:\n", raw_email_json[:200] + "...")  # 打印部分内容
    
    # 存储原始邮件（模拟数据库操作）
    try:
        email_data = json.loads(raw_email_json)
        raw_email_id = save_raw_email(
            message_id=email_data["id"],
            email_data=email_data["payload"]
        )
        
        if not raw_email_id:
            print("⚠️ 原始邮件存储失败！")
            return
    except Exception as e:
        print(f"邮件存储错误: {str(e)}")
        return

    # 解析邮件内容
    try:
        # 模拟后端解析流程
        payload = email_data["payload"]
        body_data = payload["body"]["data"]
        
        # Base64解码（模拟后端处理）
        if body_data.startswith("base64:"):
            body_data = base64.b64decode(body_data[7:]).decode('utf-8')
        else:
            body_data = base64.b64decode(body_data).decode('utf-8')
        
        # 使用解析器
        parser = GeminiParser()
        projects = parser.parse_email(body_data)
        
        print(f"\n解析出的项目数: {len(projects)}")
        for i, p in enumerate(projects, 1):
            print(f"\n项目 {i}:")
            print(f"案件内容: {p.get('案件内容','')[:50]}...")
            print(f"勤務地: {p.get('勤務地','')}")
            print(f"単価: {p.get('単価','')}")
        
        # 构建测试数据
        test_data = []
        for idx, project in enumerate(projects, 1):
            test_data.append({
                'message_id': f"real_{email_data['id']}_{idx}",
                'received_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'subject': email_data["payload"]["headers"][0]["value"],
                'sender_email': "info@engage.en-japan.com",
                'project_description': project.get("案件内容", ""),
                'required_skills': ", ".join(project.get("必須スキル", [])),
                'optional_skills': ", ".join(project.get("尚可スキル", [])),
                'location': project.get("勤務地", ""),
                'unit_price': project.get("単価", ""),
                'raw_email_id': raw_email_id,
                
            })
        
        # 写入数据库
        send_to_api(test_data)
        print("\n✅ 测试完成，数据已写入数据库")
        
    except Exception as e:
        print(f"解析过程中出错: {str(e)}")

if __name__ == "__main__":
    test_hard_case()