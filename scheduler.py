import schedule
import time
from main import main  # 假设 main.py 中有 main 函数

def job():
    print("Running scheduled job...")
    main()  # 调用你的主程序

# 每天 9 点执行任务
schedule.every().day.at("11:15").do(job)

while True:
    schedule.run_pending()
    time.sleep(60)  # 每分钟检查一次



# import schedule
# import time

# def job():
#     print("Scheduled job running...")

# # 手动执行一次任务
# job()

# # 然后继续定时执行
# schedule.every(1).minutes.do(job)

# while True:
#     schedule.run_pending()
#     time.sleep(60)
