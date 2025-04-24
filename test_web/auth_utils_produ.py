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
import pickle
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets"
]

def get_token_path(service_type):
    return f"/tmp/token_{service_type}.pickle"

def load_credentials(service_type):
    path = get_token_path(service_type)
    if os.path.exists(path):
        try:
            with open(path, 'rb') as token:
                creds = pickle.load(token)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(path, 'wb') as token:
                    pickle.dump(creds, token)
            if creds and creds.valid:
                st.session_state[f"{service_type}_authenticated"] = True
                return creds
        except Exception as e:
            if os.path.exists(path):
                os.unlink(path)
    return None

def save_credentials(service_type, creds):
    with open(get_token_path(service_type), "wb") as token:
        pickle.dump(creds, token)
    st.session_state[f"{service_type}_authenticated"] = True

def create_flow(service_type):
    oauth = st.secrets["google_oauth"]
    redirect_uri = oauth["redirect_uris"][0]
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": oauth["client_id"],
                "client_secret": oauth["client_secret"],
                "auth_uri": oauth["auth_uri"],
                "token_uri": oauth["token_uri"],
                "auth_provider_x509_cert_url": oauth["auth_provider_x509_cert_url"],
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        state=st.session_state.get("oauth_state"),
    )
    return flow

def unified_auth_flow(service_type):
    creds = load_credentials(service_type)
    if creds:
        return creds

    # 必须先设置 state
    if "oauth_state" not in st.session_state:
        st.session_state["oauth_state"] = secrets.token_urlsafe(32)

    # 然后用它创建 flow
    oauth = st.secrets["google_oauth"]
    redirect_uri = oauth["redirect_uris"][0]
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": oauth["client_id"],
                "client_secret": oauth["client_secret"],
                "auth_uri": oauth["auth_uri"],
                "token_uri": oauth["token_uri"],
                "auth_provider_x509_cert_url": oauth["auth_provider_x509_cert_url"],
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        state=st.session_state["oauth_state"]  # ✅ 用已设置的 state
    )

    if "code" not in st.query_params:
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true"
        )
        st.markdown(f'<meta http-equiv="refresh" content="0; URL={auth_url}">', unsafe_allow_html=True)
        st.stop()
    else:
        try:
            if st.query_params.get("state") != st.session_state.get("oauth_state"):
                raise ValueError("State mismatch for security")

            flow.fetch_token(code=st.query_params["code"])
            creds = flow.credentials
            save_credentials(service_type, creds)

            st.experimental_set_query_params()
            del st.session_state["oauth_state"]
            st.rerun()
        except Exception as e:
            st.error(f"認証エラー: {e}")
            token_path = get_token_path(service_type)
            if os.path.exists(token_path):
                os.unlink(token_path)
            st.stop()

    return None

def get_gmail_service():
    creds = unified_auth_flow("gmail")
    return build("gmail", "v1", credentials=creds) if creds else None

def get_sheets_service():
    creds = unified_auth_flow("sheets")
    return build("sheets", "v4", credentials=creds) if creds else None

def display_google_login():
    col1, col2 = st.columns([4, 1])
    with col1:
        if st.session_state.get("gmail_authenticated") and st.session_state.get("sheets_authenticated"):
            st.success("✅ Google認証済み - すべての機能が使用可能です")
        else:
            st.warning("⚠️ Google未認証 - 機能を使うにはログインが必要です")

    with col2:
        if st.session_state.get("gmail_authenticated") and st.session_state.get("sheets_authenticated"):
            if st.button("🔓 ログアウト"):
                for service in ["gmail", "sheets"]:
                    path = get_token_path(service)
                    if os.path.exists(path):
                        os.unlink(path)
                    st.session_state.pop(f"{service}_authenticated", None)
                st.rerun()
        else:
            if st.button("🔑 Googleでログイン"):
                unified_auth_flow("gmail")  # 最初はGmailを入口に
