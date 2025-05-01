from fastapi import FastAPI
from routers import auth, emails
from fastapi.middleware.cors import CORSMiddleware
from routers import projects
import os
from dotenv import load_dotenv
app = FastAPI()
load_dotenv()  # 加载 .env 文件中的环境变量

# 打印加载的环境变量
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')}")

# 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://ses-extractor-1.onrender.com"],  # Next.js端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/auth")

app.include_router(emails.router, prefix="/emails")
