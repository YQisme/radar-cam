import os
import time
import random

# FIFO 文件路径 (与 yolo_fifo.py 中保持一致)
fifo_path = '/home/cat/leida_test/Z_pavo2__test/send_PYTHON'

def send_signal():
    """
    向FIFO管道发送模拟信号
    每5秒发送一次 leida_ 开头的信号
    """
    # 确保FIFO管道存在
    if not os.path.exists(fifo_path):
        try:
            os.makedirs(os.path.dirname(fifo_path), exist_ok=True)
            os.mkfifo(fifo_path)
            print(f"创建FIFO管道: {fifo_path}")
        except Exception as e:
            print(f"创建FIFO管道失败: {e}")
            return

    counter = 1
    
    while True:
        try:
            print(f"尝试打开FIFO管道进行写入...")
            with open(fifo_path, 'wb') as fifo:
                print("FIFO管道已连接，开始发送模拟信号")
                
                while True:
                    signal_data = f"leida_"
                    
                    # 向管道写入数据
                    fifo.write(signal_data.encode('utf-8'))
                    fifo.flush()  # 确保数据被写入
                    
                    print(f"已发送信号 #{counter}: {signal_data}")
                    counter += 1
                    
                    # 等待5秒
                    time.sleep(5)
                    
        except BrokenPipeError:
            print("FIFO管道连接断开，等待重新连接...")
            time.sleep(1)
        except Exception as e:
            print(f"发送信号时发生错误: {e}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        print("模拟信号生成器启动，每5秒发送一次信号...")
        send_signal()
    except KeyboardInterrupt:
        print("程序被用户中断")
