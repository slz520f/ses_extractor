

import streamlit as st
from test_web.auth_utils_local import get_google_credentials, get_gmail_service, get_sheets_service
from test_web.gmail_utils import fetch_ses_emails
from test_web.sheets_utils_local import export_to_sheet
from test_web.gemini_utils_local import parse_emails_with_gemini
import os
import secrets
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import pandas as pd
import requests
from datetime import datetime

# 将解析后的数据发送到 FastAPI
def send_to_api(email_data_list):
    url = "http://127.0.0.1:8000/projects/"  # FastAPI的URL
    headers = {"Content-Type": "application/json"}
    success_count = 0
    error_count = 0
    
    for email_data in email_data_list:
        try:
            # 强化数据预处理
            processed_data = {
                "message_id": email_data['message_id'],
                "received_at": datetime.strptime(email_data['received_at'], "%Y-%m-%d %H:%M:%S").isoformat(),
                "subject": str(email_data.get('subject', '')),
                "sender_email": str(email_data.get('sender_email', '')),
                "project_description": list_to_str(email_data.get('project_description', [])),
                "required_skills": list_to_str(email_data.get('required_skills', [])),
                "optional_skills": list_to_str(email_data.get('optional_skills', [])),
                "location": list_to_str(email_data.get('location', [])),
                "unit_price": list_to_str(email_data.get('unit_price', []), max_length=500)  # 防止超长
            }

            # 发送请求
            response = requests.post(url, json=processed_data, headers=headers)
            result = response.json()
            
            # 增强响应处理
            if response.status_code == 200:
                if result.get("status") == "success":
                    success_count += 1
                    print(f"✅ {result.get('action', '操作')}成功: {processed_data['message_id']}")
                else:
                    error_count += 1
                    print(f"❌ 业务错误: {result.get('reason', '未知原因')}")
            else:
                error_count += 1
                print(f"❌ HTTP错误 [{response.status_code}]: {response.text}")
                
        except Exception as e:
            error_count += 1
            print(f"⚠️ 请求异常: {str(e)}")

def list_to_str(value, delimiter=", ", max_length=None):
    """安全处理列表转字符串"""
    if isinstance(value, list):
        joined = delimiter.join(str(item) for item in value)
        return joined[:max_length] if max_length else joined
    return str(value)[:max_length] if max_length else str(value)

# 页面配置
st.set_page_config(
    page_title="SES案件管理システム",
    page_icon="📩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    .stButton>button {
        border-radius: 5px;
        padding: 10px 24px;
        font-weight: bold;
    }
    .google-login {
        background-color: #4285F4 !important;
        color: white !important;
    }
    .google-login:hover {
        background-color: #3367D6 !important;
    }
    .success-box {
        background-color: #e8f5e9;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 20px;
    }
    .error-box {
        background-color: #ffebee;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #f44336;
        margin-bottom: 20px;
    }
    .function-btn {
        width: 100%;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# 页面标题
st.title('📩 SES案件管理システム')
st.markdown("""
<div style="margin-bottom:30px;">
    <p>これは <strong>Gmail + Gemini + Google Sheets</strong> を組み合わせたSES案件抽出ツールです。</p>
</div>
""", unsafe_allow_html=True)

def get_oauth_flow():
    """获取OAuth流程对象，兼容本地和Streamlit Cloud环境"""
    try:
        # 生产环境使用secrets
        # if st.secrets.get("google_oauth"):
        #     client_config = {
        #         "web": st.secrets["google_oauth"]
        #     }
        #     return Flow.from_client_config(
        #         client_config,
        #         scopes=[
        #             "https://www.googleapis.com/auth/gmail.readonly",
        #             "https://www.googleapis.com/auth/spreadsheets"
        #         ],
        #         redirect_uri=st.secrets.get("REDIRECT_URI", "https://ew4cdpjavj2nyqgqwbme7y.streamlit.app/")
        #     )
        
        # 本地开发使用文件
        client_secrets_path = os.path.join(os.path.dirname(__file__), 'config/client_secrets.json')
        if os.path.exists(client_secrets_path):
            return Flow.from_client_secrets_file(
                client_secrets_path,
                scopes=[
                    "https://www.googleapis.com/auth/gmail.readonly",
                    "https://www.googleapis.com/auth/spreadsheets"
                ],
                redirect_uri="http://localhost:8501/"
            )
        
        st.error("OAuth配置未找到。请在本地创建config/client_secrets.json或在Streamlit Cloud配置secrets")
        return None
        
    except Exception as e:
        st.error(f"OAuth初始化失败: {str(e)}")
        return None
    
# 认证状态检查与处理
def handle_authentication():
    # 检查现有凭证
    if 'credentials' in st.session_state:
        try:
            # 验证凭证是否有效
            if not st.session_state['credentials'].valid:
                if st.session_state['credentials'].expired and st.session_state['credentials'].refresh_token:
                    st.session_state['credentials'].refresh(Request())
                else:
                    del st.session_state['credentials']
                    return False
            return True
        except Exception as e:
            st.error(f"認証エラー: {str(e)}")
            del st.session_state['credentials']
            return False
    
    # 尝试从URL参数获取code进行自动认证
    code = st.query_params.get('code')
    if code:
        try:
            flow = get_oauth_flow()
            if flow is None:
                return False
                
            flow.fetch_token(code=code)
            st.session_state['credentials'] = flow.credentials
            st.rerun()
            return True
        except Exception as e:
            st.error(f"認証処理エラー: {str(e)}")
            return False
    
    
    
    return False

# 认证部分
st.header("🔐 Google アカウント認証", divider="rainbow")

if handle_authentication():
    st.markdown("""
    <div class="success-box">
        ✅ <strong>認証済み</strong> - システムを使用する準備ができました
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔓 ログアウト", key="logout_btn"):
        del st.session_state['credentials']
        st.rerun()
else:
    st.markdown("""
    <div style="margin-bottom:20px;">
        <p>このシステムを使用するには、まずGoogleアカウントで認証してください。</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 准备OAuth流程
    flow = get_oauth_flow()
    if flow is not None:
        # 生成并保存state
        oauth_state = secrets.token_urlsafe(16)
        st.session_state['oauth_state'] = oauth_state
       
        auth_url, _ = flow.authorization_url(
            prompt='consent',
            state=oauth_state,
            access_type='offline',
            include_granted_scopes='true',
           
        )
    
    # 单一登录按钮
    if st.button("Googleでログイン", key="google_login", help="Googleアカウントで認証します"):
        st.session_state['auth_url'] = auth_url
        # st.markdown(f'<meta http-equiv="refresh" content="0; url={auth_url}">', unsafe_allow_html=True)
        st.write(f"[👉 Googleでログイン]({auth_url})", unsafe_allow_html=True)


# 功能部分 (仅认证用户可见)
if 'credentials' in st.session_state:
    st.header("📥 メール取得・解析", divider="rainbow")
    
    # 邮件获取与解析
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("① GmailからSESメールを取得")
        if st.button('📨 メールを取得', key="fetch_emails", help="GmailからSES関連のメールを取得します"):
            with st.spinner('メールを取得中...'):
                try:
                    service = get_gmail_service()
                    if service is None:
                        st.error("Gmailサービスに接続できませんでした。認証を確認してください。")
                    else:
                        progress_bar = st.progress(0)
                        emails = fetch_ses_emails(service, progress_bar)
                        st.session_state['emails'] = emails
                        st.success(f"📥 メール取得完了：{len(emails)}件")
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")

                
    
    with col2:
        st.subheader("🔑 Gemini API Key 設定（任意）")
        user_api_key = st.text_input("Gemini API Key を入力してください（任意）", type="password")

        if user_api_key:
            st.session_state["user_gemini_api_key"] = user_api_key
            st.success("✅ Gemini API Key が保存されました")    
        
        

        st.subheader("② メール内容をGeminiで解析")
        if st.button('🤖 Geminiで解析', key="analyze_emails", help="取得したメールをGeminiで解析します"):
            if 'emails' not in st.session_state:
                st.error("⚠️ 先に『メールを取得』を実行してください")
            else:
                with st.spinner('メールを解析中...'):
                    try:
                        progress_bar = st.progress(0)
                        progress_text = st.empty()  # 新增：用于显示百分比

                        def progress_callback(p):
                            percent = int(p * 100)
                            progress_bar.progress(p)
                            progress_text.markdown(f"**進捗：{percent}%**")

                        email_data_list = parse_emails_with_gemini(
                            st.session_state['emails'], 
                            progress_callback=progress_callback,
                            api_key=st.session_state.get("user_gemini_api_key")  # 如果有用户key就用    
                        )

                         # 发送数据到 FastAPI 后端
                        send_to_api(email_data_list)

                        st.session_state['email_data_list'] = email_data_list
                        st.success(f"🧠 メール解析完了！ {len(email_data_list)}件のデータを生成しました")
                    except Exception as e:
                        st.error(f"解析中にエラーが発生しました: {str(e)}")


                       
                        
                
    


    if 'email_data_list' in st.session_state:
        st.subheader("📊 解析結果プレビュー")
        
        email_df = pd.DataFrame(st.session_state['email_data_list'])
        email_df = email_df.convert_dtypes()
        email_df = email_df.fillna('')  # 或者 .astype(str)

        # 将列表或字典转成字符串，避免 pyarrow 报错
        for col in email_df.columns:
            email_df[col] = email_df[col].apply(
                lambda x: ', '.join(map(str, x)) if isinstance(x, list)
                else str(x) if isinstance(x, dict)
                else x
            )

        st.dataframe(email_df, use_container_width=True)
    








    # 导出到Google Sheets
    # st.header("📤 データエクスポート", divider="rainbow")
    
    # col1, col2 = st.columns([3, 1])
    # with col1:
    #     spreadsheet_id = st.text_input(
    #         'Google SheetsのスプレッドシートID',
    #         help="例: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    #     )
    # with col2:
    #     sheet_name = st.text_input(
    #         'シート名',
    #         value="シート1",
    #         help="既存のシート名を指定するか、新規シート名を入力してください"
    #     )
    
    # if st.button('📤 Google Sheetsに書き込む', key="export_to_sheet", help="解析結果をGoogle Sheetsにエクスポートします"):
    #     if not spreadsheet_id:
    #         st.error("🆔 スプレッドシートIDを入力してください")
    #     elif 'email_data_list' not in st.session_state:
    #         st.error("⚠️ データがありません。先にメール解析を実行してください")
    #     else:
    #         with st.spinner('Google Sheetsに書き込み中...'):
    #             try:
    #                 service = get_sheets_service()  # 确保使用正确的函数名
    #                 if service is None:
    #                     st.error("Google Sheetsサービスに接続できませんでした。認証を確認してください。")
    #                 else:
    #                     export_to_sheet(
    #                         email_data_list=st.session_state['email_data_list'],
    #                         spreadsheet_id=spreadsheet_id,
    #                         sheet_name=sheet_name
    #                     )
    #                     st.success("✅ Google Sheetsへの書き込みが完了しました！")
    #             except RefreshError:
    #                 st.error("セッションがタイムアウトしました。再度ログインしてください。")
    #                 if 'credentials' in st.session_state:
    #                     del st.session_state['credentials']
    #                 st.rerun()
    #             except Exception as e:
    #                 st.error(f"書き込み中にエラーが発生しました: {str(e)}")