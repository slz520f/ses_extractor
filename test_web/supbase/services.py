from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from fastapi import HTTPException
import os

# 假设你会将凭证存储在 FastAPI 会话管理的某个地方
# 例如，可以使用 `session` 或直接在数据库/缓存中存储
def get_google_credentials():
    """获取有效的Google凭证"""
    creds = None
    
    # 从某个位置（例如数据库、缓存）获取凭证，这里假设它已经存储在某个地方
    if 'credentials' in session_state:
        creds = session_state['credentials']
        
        # 验证凭证有效性
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    session_state['credentials'] = creds  # 更新凭证
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"凭证刷新失败: {e}")
            else:
                return None
        return creds
    return None

def get_gmail_service():
    """获取Gmail服务实例"""
    creds = get_google_credentials()
    if creds:
        try:
            return build('gmail', 'v1', credentials=creds)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gmail服务初始化失败: {e}")
    return None

def get_sheets_service():
    """获取Google Sheets服务实例"""
    creds = get_google_credentials()
    if creds:
        try:
            return build('sheets', 'v4', credentials=creds)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Sheets服务初始化失败: {e}")
    return None
