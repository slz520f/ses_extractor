import streamlit as st
import pandas as pd
from test.export_to_sheets_test import get_db_data, export_to_sheet





# ヘッダー
st.title('SES案件管理システム')

# データを表示する
st.header('データベースのデータ')
df = get_db_data()
if df.empty:
    st.warning("データがありません")
else:
    st.dataframe(df)

# Google Sheetsへのエクスポート
st.header('Google Sheetsへのエクスポート')
spreadsheet_id = st.text_input('Google SheetsのスプレッドシートIDを入力', '')

if st.button('エクスポート'):
    if spreadsheet_id:
        export_to_sheet(spreadsheet_id)
        st.success("データがGoogle Sheetsにエクスポートされました")
    else:
        st.error("スプレッドシートIDを入力してください")
