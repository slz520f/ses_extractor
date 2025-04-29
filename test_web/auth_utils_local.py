





import os
import secrets
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets"
]

def validate_credentials(creds):
    """验证并刷新凭证（如果需要）"""
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                return creds
            except Exception as e:
                st.error(f"凭证刷新失败: {e}")
                return None
        return None
    return creds

def get_google_credentials():
    """获取有效的Google凭证"""
    creds = None
    
    # 检查session state中的凭证
    if 'credentials' in st.session_state:
        creds = st.session_state['credentials']
        
        # 验证凭证有效性
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    st.session_state['credentials'] = creds
                except Exception as e:
                    st.error(f"凭证刷新失败: {e}")
                    return None
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
            st.error(f"Gmail服务初始化失败: {e}")
            return None
    return None

def get_sheets_service():
    """获取Google Sheets服务实例"""
    creds = get_google_credentials()
    if creds:
        try:
            return build('sheets', 'v4', credentials=creds)
        except Exception as e:
            st.error(f"Sheets服务初始化失败: {e}")
            return None
    return None

# 在主页使用的登录函数
def display_google_login():
    """在主页显示Google登录按钮并处理认证流程"""
    if 'credentials' not in st.session_state:
        # 准备OAuth流程
        flow = Flow.from_client_secrets_file(
            'config/client_secrets.json',
            scopes=SCOPES,
            redirect_uri=os.getenv('REDIRECT_URI', 'http://localhost:8501/')
        )
        
        # 生成并保存state
        oauth_state = secrets.token_urlsafe(16)
        st.session_state['oauth_state'] = oauth_state
        
        auth_url, _ = flow.authorization_url(
            prompt='consent',
            state=oauth_state,
            access_type='offline',
            include_granted_scopes='true'
        )
        
        # 显示登录按钮（直接使用Streamlit按钮）
        if st.button("Googleアカウントでログイン", key="google_login"):
            st.session_state['auth_url'] = auth_url
            st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
    else:
        st.success("✅ すでにログイン済みです")
        if st.button("ログアウト", key="logout"):
            del st.session_state['credentials']
            st.rerun()