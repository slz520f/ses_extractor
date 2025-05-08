from fastapi import FastAPI
from routers import auth, emails
from fastapi.middleware.cors import CORSMiddleware
from routers import projects
import os
from dotenv import load_dotenv
# ロギング設定を追加（main.pyなどに）
import logging
logging.basicConfig(level=logging.DEBUG)
app = FastAPI()
load_dotenv()  # 加载 .env 文件中的环境变量

# 打印加载的环境变量
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')}")
# PostgreSQL接続設定
print(f"POSTGRES_HOST: {os.getenv('POSTGRES_HOST')}")
print(f"POSTGRES_DB: {os.getenv('POSTGRES_DB')}")
print(f"POSTGRES_USER: {os.getenv('POSTGRES_USER')}")

# 允许前端访问
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["https://ses-extractor.onrender.com","https://ses-extractor-1.onrender.com"], 
    allow_origins=["http://localhost:3000"] ,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/auth")

app.include_router(emails.router, prefix="/emails")
