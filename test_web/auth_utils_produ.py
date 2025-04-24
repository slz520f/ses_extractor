# import pickle
# import os
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from google.auth.transport.requests import Request
# import os
# import streamlit as st
# from google_auth_oauthlib.flow import Flow
# from google.auth.transport.requests import Request
# import pickle




# from google_auth_oauthlib.flow import Flow
# from googleapiclient.discovery import build
# import streamlit as st

# SCOPES = [
#     "https://www.googleapis.com/auth/gmail.readonly",
#     "https://www.googleapis.com/auth/spreadsheets"
# ]

# def get_google_credentials():
#     creds = None
#     if 'credentials' in st.session_state:
#         creds = st.session_state['credentials']
#     else:
#         # 获取 URL 参数中的 code
#         code = st.experimental_get_query_params().get('code', [None])[0]
        
#         if code:
#             try:
#                 # 使用 code 获取访问令牌
#                 flow = Flow.from_client_secrets_file(
#                     'config/client_secrets.json',
#                     scopes=SCOPES,
#                     redirect_uri='http://localhost:8501/'  # 这个必须和你在 Google Cloud Console 中配置的一致
#                 )
#                 flow.fetch_token(code=code)
#                 creds = flow.credentials
#                 st.session_state['credentials'] = creds
#                 st.success("✅ 認証に成功しました！")
#             except Exception as e:
#                 st.error(f"認証エラー: {e}")
                
#     return creds

# # 然后使用 Gmail API：
# def get_gmail_service():
#     creds = get_google_credentials()
#     return build('gmail', 'v1', credentials=creds)

# # 使用 Sheets API：
# def get_sheets_service():
#     creds = get_google_credentials()
#     return build('sheets', 'v4', credentials=creds)








# import os
# import pickle
# import streamlit as st
# from google_auth_oauthlib.flow import Flow
# from googleapiclient.discovery import build
# from google.auth.transport.requests import Request

# SCOPES = [
#     "https://www.googleapis.com/auth/gmail.readonly",
#     "https://www.googleapis.com/auth/spreadsheets"
# ]

# def get_google_credentials():
#     creds = None
#     # Check if credentials are already stored in session state
#     if 'credentials' in st.session_state:
#         creds = st.session_state['credentials']
#     else:
#         # Get code from URL query parameters
#         code = st.query_params.get('code', [None])[0]
        
#         if code:
#             try:
#                 # Use the code to fetch the token
#                 flow = Flow.from_client_secrets_file(
#                     'config/client_secrets.json',
#                     scopes=SCOPES,
#                     redirect_uri='http://localhost:8501/'  # Make sure this matches your Google Cloud Console settings
#                 )
#                 flow.fetch_token(code=code)
#                 creds = flow.credentials
#                 st.session_state['credentials'] = creds
#                 st.success("✅ 認証に成功しました！")
#             except Exception as e:
#                 st.error(f"認証エラー: {e}")
                
#     return creds

# # Gmail API service
# def get_gmail_service():
#     creds = get_google_credentials()
#     if creds:
#         return build('gmail', 'v1', credentials=creds)
#     return None

# # Google Sheets API service
# def get_sheets_service():
#     creds = get_google_credentials()
#     if creds:
#         return build('sheets', 'v4', credentials=creds)
#     return None








# from google_auth_oauthlib.flow import Flow
# from googleapiclient.discovery import build
# import streamlit as st

# SCOPES = [
#     "https://www.googleapis.com/auth/gmail.readonly",
#     "https://www.googleapis.com/auth/spreadsheets"
# ]

# def get_google_credentials():
#     creds = None
#     if 'credentials' in st.session_state:
#         creds = st.session_state['credentials']
#     else:
#         code = st.query_params.get('code', [None])[0]  # ✅ 自动获取 URL 中的 code
#         if code:
#             try:
#                 flow = Flow.from_client_secrets_file(
#                     'config/client_secrets.json',
#                     scopes=SCOPES,
#                     redirect_uri='http://localhost:8501/'  # 和授权时保持一致
#                 )
#                 flow.fetch_token(code=code)
#                 creds = flow.credentials
#                 st.session_state['credentials'] = creds
#                 st.success("✅ 認証に成功しました！")
#             except Exception as e:
#                 st.error(f"認証エラー: {e}")
#         else:
#             # 初次访问：显示登录链接
#             flow = Flow.from_client_secrets_file(
#                 'config/client_secrets.json',
#                 scopes=SCOPES,
#                 redirect_uri='http://localhost:8501/'
#             )
#             auth_url, _ = flow.authorization_url(prompt='consent')
#             st.markdown(f"👉 [Googleアカウントでログイン]({auth_url})")

#     return creds

# # 然后使用 Gmail API：
# def get_gmail_service():
#     creds = get_google_credentials()
#     return build('gmail', 'v1', credentials=creds)

# # 使用 Sheets API：
# def get_sheets_service():
#     creds = get_google_credentials()
#     return build('sheets', 'v4', credentials=creds)






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
        oauth_secrets = st.secrets["google_oauth"]
        
        # 确保重定向URI正确
        redirect_uri = oauth_secrets["redirect_uris"][0] if isinstance(oauth_secrets["redirect_uris"], list) else oauth_secrets["redirect_uris"]
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": oauth_secrets["client_id"],
                    "client_secret": oauth_secrets["client_secret"],
                    "project_id": oauth_secrets["project_id"],
                    "auth_uri": oauth_secrets["auth_uri"],
                    "token_uri": oauth_secrets["token_uri"],
                    "auth_provider_x509_cert_url": oauth_secrets["auth_provider_x509_cert_url"],
                    "redirect_uris": [redirect_uri]  # 确保是列表形式
                }
            },
            scopes=SCOPES,
            redirect_uri=redirect_uri
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
        
        if st.button("Googleアカウントでログイン", key="google_login"):
            st.session_state['auth_url'] = auth_url
            st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
    else:
        st.success("✅ すでにログイン済みです")
        if st.button("ログアウト", key="logout"):
            del st.session_state['credentials']
            st.rerun()