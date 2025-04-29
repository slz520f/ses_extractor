from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional
import logging
from fastapi.responses import JSONResponse


# 加载环境变量
load_dotenv()

app = FastAPI()

# 配置 Supabase
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# 增强日志配置
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG)

class ProjectData(BaseModel):
    received_at: str  # 使用字符串接收，后续转换
    subject: str
    sender_email: str
    project_description: str
    required_skills: Optional[str] = None
    optional_skills: Optional[str] = None
    location: Optional[str] = None
    unit_price: Optional[str] = None
    message_id: str

@app.post("/projects")
async def add_project(project: ProjectData):
    logger.debug(f"接收原始数据: {project.dict()}")
    try:
        # 1. 检查数据有效性
        if not project.message_id:
            return JSONResponse(
                status_code=200,
                content={"status": "error", "reason": "message_id不能为空"}
            )
        
        # 转换时间格式
        received_at = datetime.fromisoformat(project.received_at)
        
        # 构建插入数据
        insert_data = {
            "received_at": received_at.isoformat(),
            "subject": project.subject,
            "sender_email": project.sender_email,
            "project_description": project.project_description,
            "required_skills": project.required_skills or None,
            "optional_skills": project.optional_skills or None,
            "location": project.location or None,
            "unit_price": project.unit_price or None,
            "message_id": project.message_id
        }

        # 2. 检查重复（使用UPSERT方式）
        response = supabase.table('ses_projects') \
            .upsert(
                {
                    "received_at": received_at.isoformat(),
                    "subject": project.subject,
                    "sender_email": project.sender_email,
                    "project_description": project.project_description,
                    "required_skills": project.required_skills or None,
                    "optional_skills": project.optional_skills or None,
                    "location": project.location or None,
                    "unit_price": project.unit_price or None,
                    "message_id": project.message_id
                },
                on_conflict="message_id"
            ).execute()
        
        # 3. 统一响应格式
        if response.data:
            return {
                "status": "success",
                "action": "inserted" if len(response.data) > 0 else "updated",
                "id": response.data[0]['id']
            }
        else:
            return JSONResponse(
                status_code=200,
                content={"status": "error", "reason": "数据库操作失败"}
            )

    except Exception as e:
        logger.error(f"处理异常: {str(e)}")
        return JSONResponse(
            status_code=200,
            content={"status": "error", "reason": str(e)}
        )
    


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)






from fastapi import FastAPI
from test_web.supbase.auth import router as auth_router

app = FastAPI()

# 引入认证相关的路由
app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/")
def read_root():
    return {"message": "Hello, this is the main app!"}
