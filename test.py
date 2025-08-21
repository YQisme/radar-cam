import os
import fcntl
import threading
import time

# FIFO 文件路径
fifo_path = '/home/cat/test_1/fifo_pipe_2/send_PYTHON'
fifo1_path = '/home/cat/test_1/fifo_pipe_2/rece_PYTHON'

def read_from_fifo():
    with open(fifo_path, 'rb') as fifo:
        fd = fifo.fileno()

        # 设置 FIFO 为非阻塞模式
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        while True:
            try:
                # 尝试读取数据
                data = fifo.read()
                if data:
                    print(f"Received: {data.decode('utf-8', 'ignore')}")
            except IOError:
                # 如果没有数据，捕获异常并跳过
                pass
            time.sleep(0.1)  # 给 CPU 一些休息时间

def write_to_fifo1():
    with open(fifo1_path, 'wb') as fifo1:
        while True:
            # 每隔 1 秒向 fifo1 写入数据
            fifo1.write(b"hello from python\n")
            fifo1.flush()  # 确保数据被写入
            print("Sent: hello from python")
            time.sleep(1)

if __name__ == '__main__':
    # 创建线程
    read_thread = threading.Thread(target=read_from_fifo)
    write_thread = threading.Thread(target=write_to_fifo1)

    # 启动线程
    read_thread.start()
    write_thread.start()

    # 等待线程结束
    read_thread.join()
    write_thread.join()
