import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from dotenv import load_dotenv 
import mysql.connector
import os
import matplotlib.font_manager as fm

# 设置字体路径
path = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"  # macOS 中的字体路径
jp_font = fm.FontProperties(fname=path).get_name()

plt.rcParams["font.family"] = jp_font
plt.rcParams['axes.unicode_minus'] = False  # 避免负号显示错误


# .envファイルを読み込む
load_dotenv()

# .envからMySQL設定を取得
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')


def get_db_connection():
    if not all([MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE]):
        print("MySQLの設定が不足しています。確認してください。")
        return None, None
    
    try:
        # MySQLに接続
        print("正在尝试连接到数据库...")
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        
        # 接続成功時にカーソルを作成
        print("データベース接続成功")
        cursor = conn.cursor()
        return conn
    except mysql.connector.Error as err:
        print(f"データベース接続失敗: {err}")
        return None, None
    except Exception as e:
        print(f"設定読み込み失敗: {e}")
        return None, None

# 🌟 単価分布のヒストグラム
def visualize_unit_price_distribution():
    conn=get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT unit_price FROM ses_projects WHERE unit_price IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows)

    plt.figure(figsize=(10, 6))
    sns.histplot(df['unit_price'], bins=20, kde=True, color='skyblue')
    plt.title("案件単価の分布", fontsize=14)
    plt.xlabel("単価（円）")
    plt.ylabel("案件数")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# 📈 月別の案件数推移



# 📍 勤務地の頻度（棒グラフ）
def visualize_location_counts(top_n=10):
    conn=get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT location FROM ses_projects WHERE location IS NOT NULL")

    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows)
    location_counts = df['location'].value_counts().head(top_n)

    plt.figure(figsize=(10, 6))
    sns.barplot(x=location_counts.values, y=location_counts.index, palette='viridis')
    plt.title(f"勤務地の上位 {top_n} 件数", fontsize=14)
    plt.xlabel("件数")
    plt.ylabel("勤務地")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# 🔍 スキルキーワードの出現頻度（簡易カウント）
def visualize_skill_keywords(top_n=10):
    conn=get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT required_skills FROM ses_projects WHERE required_skills IS NOT NULL")
    rows = cursor.fetchall()
    conn.close()

    df = pd.DataFrame(rows)

    # キーワード抽出（簡易版：空白区切り）
    from collections import Counter
    all_words = " ".join(df['required_skills'].tolist()).split()
    word_counts = Counter(all_words)

    most_common = word_counts.most_common(top_n)
    words, counts = zip(*most_common)

    plt.figure(figsize=(10, 6))
    sns.barplot(x=list(counts), y=list(words), palette='cool')
    plt.title(f"スキルキーワードの上位 {top_n}", fontsize=14)
    plt.xlabel("出現回数")
    plt.ylabel("キーワード")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# ✅ スクリプトとして実行できるように
if __name__ == "__main__":
    print("📊 可視化開始！")
    visualize_unit_price_distribution()
    
    visualize_location_counts(top_n=10)
    visualize_skill_keywords(top_n=15)
