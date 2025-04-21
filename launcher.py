import subprocess
import webbrowser
import time
import threading

# 启动 Streamlit 服务
def run_streamlit():
    # 启动 streamlit 服务并获取输出
    result = subprocess.Popen(
        ["/Users/mame/ses_extractor/venv/bin/python", "-m", "streamlit", "run", "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result

# 通过捕获 Streamlit 输出动态获取端口号
def get_streamlit_port():
    result = subprocess.run(
        ["/Users/mame/ses_extractor/venv/bin/python", "-m", "streamlit", "config", "show"],
        capture_output=True, text=True
    )
    # 获取端口号
    for line in result.stdout.splitlines():
        if line.strip().startswith("browser.serverPort"):
            port = int(line.split(":")[1].strip())
            return port
    return 8501  # 默认端口

# 启动服务 + 打开浏览器
def launch_app():
    # 启动 Streamlit 服务
    streamlit_process = threading.Thread(target=run_streamlit)
    streamlit_process.start()
    time.sleep(2)  # 等待服务启动

    # 获取并打开浏览器
    port = get_streamlit_port()
    print(f"Streamlit 服务已启动，端口号: {port}")
    webbrowser.open(f"http://localhost:{port}")

if __name__ == "__main__":
    launch_app()
