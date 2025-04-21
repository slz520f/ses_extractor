import streamlit as st
from google_auth_oauthlib.flow import Flow
import os
import pickle

st.set_page_config(page_title="SES案件管理", page_icon="📧")

# 准备 Google OAuth flow
def get_flow():
    from urllib.parse import quote

    return Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["google"]["client_id"],
                "client_secret": st.secrets["google"]["client_secret"],
                "redirect_uris": ["http://localhost:8501"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/spreadsheets"
        ],
        redirect_uri="http://localhost:8501"
    )

# 登录按钮
if "credentials" not in st.session_state:
    st.title("🔐 SES案件抽出システム - ログイン")
    flow = get_flow()
    auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
    st.markdown(f"[Googleでログイン]({auth_url})")

# 登录完成后，手动提取 code 并验证（开发用）
code = st.query_params.get("code")
if code and "credentials" not in st.session_state:
    flow = get_flow()
    flow.fetch_token(code=code[0])
    credentials = flow.credentials
    st.session_state["credentials"] = credentials
    st.success("✅ ログイン成功しました")

# 已登录用户信息
if "credentials" in st.session_state:
    st.title("👤 ログイン済み")
    st.write(f"Access Token: {st.session_state['credentials'].token}")
    st.write("ここから Gmail 読取へ進めます ✅")
