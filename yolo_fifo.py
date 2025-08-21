import os
import fcntl
import threading
import time
import cv2
from ultralytics import YOLO

# FIFO 文件路径
fifo_path = '/home/cat/leida_test/Z_pavo2__test/send_PYTHON'
fifo1_path = '/home/cat/leida_test/Z_pavo2__test/rece_PYTHON'

# RTSP 摄像头源
source = "rtsp://admin:scyzkj123456@192.168.0.2:554/h264/ch1/main/av_stream"

# 加载预训练的 YOLO 模型
model = YOLO("yolo11n.pt")

# 全局变量，用于控制YOLO识别
yolo_running = False
person_detected = False
last_person_detection_time = 0
person_detection_timeout = 10  # 10秒无人检测则自动关闭YOLO

# 创建锁，用于线程间同步
yolo_lock = threading.Lock()
# 视频流资源锁
stream_lock = threading.Lock()

# 视频流对象
stream = None
cap = None

def init_video_stream():
    """初始化视频流，返回视频捕获对象"""
    global cap
    try:
        if cap is not None:
            cap.release()
        
        # 使用OpenCV直接打开RTSP流
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print("无法打开视频流")
            return None
        
        print("成功连接到视频流")
        return cap
    except Exception as e:
        print(f"初始化视频流时发生错误: {e}")
        return None

def release_video_stream():
    """释放视频流资源"""
    global cap
    try:
        if cap is not None:
            cap.release()
            cap = None
            print("已释放视频流资源")
    except Exception as e:
        print(f"释放视频流资源时发生错误: {e}")

def run_yolo_detection():
    global yolo_running, person_detected, last_person_detection_time, cap
    print("启动YOLO识别...")
    
    try:
        with stream_lock:
            # 初始化视频流
            if cap is None or not cap.isOpened():
                cap = init_video_stream()
                if cap is None:
                    print("无法初始化视频流，YOLO识别终止")
                    with yolo_lock:
                        yolo_running = False
                    return
        
        # 设置初始时间
        last_activity_time = time.time()
        
        while True:
            try:
                with stream_lock:
                    if cap is None or not cap.isOpened():
                        print("视频流已关闭，重新初始化")
                        cap = init_video_stream()
                        if cap is None:
                            break
                    
                    # 读取一帧
                    ret, frame = cap.read()
                    if not ret:
                        print("无法读取视频帧，尝试重新初始化视频流")
                        cap = init_video_stream()
                        continue
                
                # 使用YOLO模型进行目标检测
                results = model.track(frame, stream=False)  # 单帧处理，不使用流模式
                
                person_found = False
                
                # 检查是否识别到人
                if len(results) > 0 and len(results[0].boxes) > 0:
                    for box in results[0].boxes:
                        if hasattr(box, 'cls'):
                            cls = int(box.cls[0])
                            cls_name = results[0].names[cls]
                            if cls_name == "person":
                                print("检测到人！")
                                person_found = True
                                with yolo_lock:
                                    person_detected = True
                                    last_person_detection_time = time.time()
                                break
                
                # 如果没有检测到人，检查是否超时
                if not person_found:
                    current_time = time.time()
                    time_since_last_detection = current_time - last_person_detection_time
                    
                    if last_person_detection_time > 0 and time_since_last_detection > person_detection_timeout:
                        print(f"已超过{person_detection_timeout}秒未检测到人，自动停止YOLO识别")
                        with yolo_lock:
                            yolo_running = False
                
                # 如果不再运行，退出循环
                with yolo_lock:
                    if not yolo_running:
                        break
                
                # 控制处理速度，避免CPU过载
                time.sleep(0.1)
                
            except Exception as e:
                print(f"YOLO检测过程中发生错误: {e}")
                time.sleep(1)  # 出错后等待一段时间再继续
    
    finally:
        # 确保在退出时释放资源
        with stream_lock:
            release_video_stream()
        
        print("YOLO识别已停止")

def check_yolo_timeout():
    """检查YOLO是否需要超时关闭的线程函数"""
    global yolo_running, last_person_detection_time
    
    while True:
        time.sleep(1)  # 每秒检查一次
        
        with yolo_lock:
            if yolo_running and last_person_detection_time > 0:
                current_time = time.time()
                time_since_last_detection = current_time - last_person_detection_time
                
                if time_since_last_detection > person_detection_timeout:
                    print(f"已超过{person_detection_timeout}秒未检测到人，自动停止YOLO识别")
                    yolo_running = False

def read_from_fifo():
    global yolo_running, last_person_detection_time
    
    while True:
        try:
            # 尝试打开FIFO管道，如果管道不存在则创建
            if not os.path.exists(fifo_path):
                os.makedirs(os.path.dirname(fifo_path), exist_ok=True)
                os.mkfifo(fifo_path)
                print(f"创建FIFO管道: {fifo_path}")
            
            print("等待连接到FIFO管道...")
            with open(fifo_path, 'rb') as fifo:
                print("已连接到FIFO管道")
                fd = fifo.fileno()

                # 设置 FIFO 为非阻塞模式
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

                yolo_thread = None
                
                # 持续读取FIFO管道内容
                while True:
                    try:
                        # 尝试读取数据
                        data = fifo.read()
                        if data:
                            data_str = data.decode('utf-8', 'ignore')
                            print(f"Received: {data_str}")
                            
                            # 检测是否包含 "leida_" 字符串
                            if "leida_" in data_str:
                                with yolo_lock:
                                    if not yolo_running:
                                        yolo_running = True
                                        last_person_detection_time = time.time()  # 重置时间
                                        # 启动YOLO识别线程
                                        if yolo_thread is not None and yolo_thread.is_alive():
                                            print("等待旧的YOLO线程结束...")
                                            yolo_thread.join(timeout=2)
                                        
                                        yolo_thread = threading.Thread(target=run_yolo_detection)
                                        yolo_thread.daemon = True
                                        yolo_thread.start()
                                    else:
                                        print("YOLO识别已在运行中")
                            
                            # 如果收到停止命令，停止YOLO识别
                            elif "stop_yolo" in data_str:
                                with yolo_lock:
                                    if yolo_running:
                                        yolo_running = False
                                        print("手动停止YOLO识别")
                        
                    except IOError:
                        # 如果没有数据，捕获异常并跳过
                        pass
                    
                    except BrokenPipeError:
                        print("FIFO管道连接断开")
                        break
                    
                    time.sleep(0.1)  # 给 CPU 一些休息时间
        
        except Exception as e:
            print(f"读取FIFO管道时发生错误: {e}")
        
        # 如果连接断开，等待一段时间后重新尝试连接
        print("正在重新连接FIFO管道...")
        time.sleep(1)

def write_to_fifo1():
    global person_detected
    
    while True:
        try:
            # 确保FIFO管道存在
            if not os.path.exists(fifo1_path):
                os.makedirs(os.path.dirname(fifo1_path), exist_ok=True)
                os.mkfifo(fifo1_path)
                print(f"创建FIFO管道: {fifo1_path}")
            
            print("准备写入FIFO管道...")
            with open(fifo1_path, 'wb') as fifo1:
                print("已连接到写入FIFO管道")
                last_sent = False  # 记录上次是否发送了person消息
                
                while True:
                    try:
                        # 如果检测到人，向管道发送 "person"
                        with yolo_lock:
                            local_person_detected = person_detected
                            if local_person_detected:
                                person_detected = False  # 重置检测标志
                        
                        if local_person_detected:
                            if not last_sent:  # 只有当状态改变时才发送
                                fifo1.write(b"person\0")
                                fifo1.flush()  # 确保数据被写入
                                print("Sent: person")
                                last_sent = True
                        else:
                            if last_sent:  # 状态改变，重置标志
                                last_sent = False
                        
                        time.sleep(0.5)  # 每0.5秒检查一次
                    
                    except BrokenPipeError:
                        print("写入FIFO管道连接断开")
                        break
        
        except Exception as e:
            print(f"写入FIFO管道时发生错误: {e}")
        
        # 如果连接断开，等待一段时间后重新尝试连接
        print("正在重新连接写入FIFO管道...")
        time.sleep(1)

if __name__ == '__main__':
    # 创建线程
    read_thread = threading.Thread(target=read_from_fifo)
    write_thread = threading.Thread(target=write_to_fifo1)
    timeout_thread = threading.Thread(target=check_yolo_timeout)

    # 设置为守护线程，这样主程序退出时线程也会退出
    read_thread.daemon = True
    write_thread.daemon = True
    timeout_thread.daemon = True

    # 启动线程
    read_thread.start()
    write_thread.start()
    timeout_thread.start()

    try:
        # 主线程保持运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("程序被用户中断")
        # 确保在退出时释放所有资源
        with stream_lock:
            release_video_stream()