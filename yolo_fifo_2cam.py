import os
import fcntl
import threading
import time
import cv2
from ultralytics import YOLO

# FIFO 文件路径
fifo_path = '/home/cat/leida_test/Z_pavo2__test/send_PYTHON'
fifo1_path = '/home/cat/leida_test/Z_pavo2__test/rece_PYTHON'

# USB摄像头源
camera_sources = {
    "cam1": "/dev/video1",  # 第一个USB摄像头
    "cam2": "/dev/video3"   # 第二个USB摄像头
}

# 加载预训练的 YOLO 模型
models = {
    "cam1": YOLO("yolo11n_rknn_model"),
    "cam2": YOLO("yolo11n_rknn_model")
}

# 全局变量，用于控制YOLO识别
yolo_status = {
    "cam1": {
        "running": False,
        "person_detected": False,
        "last_detection_time": 0
    },
    "cam2": {
        "running": False,
        "person_detected": False,
        "last_detection_time": 0
    }
}
person_detection_timeout = 10  # 10秒无人检测则自动关闭YOLO

# 创建锁，用于线程间同步
yolo_locks = {
    "cam1": threading.Lock(),
    "cam2": threading.Lock()
}
# 视频流资源锁
stream_locks = {
    "cam1": threading.Lock(),
    "cam2": threading.Lock()
}

# 视频流对象
cameras = {
    "cam1": None,
    "cam2": None
}

def init_video_stream(camera_id):
    """初始化视频流，返回视频捕获对象"""
    try:
        if cameras[camera_id] is not None:
            cameras[camera_id].release()
        
        # 使用OpenCV打开USB摄像头
        source = camera_sources[camera_id]
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"无法打开USB摄像头 {source}")
            return None
        
        # 设置摄像头参数（根据需要调整）
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        print(f"成功连接到USB摄像头 {source}")
        cameras[camera_id] = cap
        return cap
    except Exception as e:
        print(f"初始化视频流 {camera_id} 时发生错误: {e}")
        return None

def release_video_stream(camera_id):
    """释放视频流资源"""
    try:
        if cameras[camera_id] is not None:
            cameras[camera_id].release()
            cameras[camera_id] = None
            print(f"已释放摄像头 {camera_id} 资源")
    except Exception as e:
        print(f"释放摄像头 {camera_id} 资源时发生错误: {e}")

def run_yolo_detection(camera_id):
    """为指定摄像头运行YOLO检测"""
    print(f"启动摄像头 {camera_id} 的YOLO识别...")
    
    try:
        with stream_locks[camera_id]:
            # 初始化视频流
            if cameras[camera_id] is None or not cameras[camera_id].isOpened():
                cap = init_video_stream(camera_id)
                if cap is None:
                    print(f"无法初始化摄像头 {camera_id}，YOLO识别终止")
                    with yolo_locks[camera_id]:
                        yolo_status[camera_id]["running"] = False
                    return
        
        # 获取对应摄像头的YOLO模型
        model = models[camera_id]
        
        # 设置初始时间
        last_activity_time = time.time()
        
        while True:
            try:
                with stream_locks[camera_id]:
                    cap = cameras[camera_id]
                    if cap is None or not cap.isOpened():
                        print(f"摄像头 {camera_id} 视频流已关闭，重新初始化")
                        cap = init_video_stream(camera_id)
                        if cap is None:
                            break
                    
                    # 读取一帧
                    ret, frame = cap.read()
                    if not ret:
                        print(f"无法从摄像头 {camera_id} 读取视频帧，尝试重新初始化")
                        cap = init_video_stream(camera_id)
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
                                print(f"摄像头 {camera_id} 检测到人！")
                                person_found = True
                                with yolo_locks[camera_id]:
                                    yolo_status[camera_id]["person_detected"] = True
                                    yolo_status[camera_id]["last_detection_time"] = time.time()
                                break
                
                # 如果没有检测到人，检查是否超时
                if not person_found:
                    current_time = time.time()
                    last_detection = yolo_status[camera_id]["last_detection_time"]
                    time_since_last_detection = current_time - last_detection
                    
                    if last_detection > 0 and time_since_last_detection > person_detection_timeout:
                        print(f"摄像头 {camera_id} 已超过{person_detection_timeout}秒未检测到人，自动停止YOLO识别")
                        with yolo_locks[camera_id]:
                            yolo_status[camera_id]["running"] = False
                
                # 如果不再运行，退出循环
                with yolo_locks[camera_id]:
                    if not yolo_status[camera_id]["running"]:
                        break
        
                # 控制处理速度，避免CPU过载
                time.sleep(0.1)
                
            except Exception as e:
                print(f"摄像头 {camera_id} YOLO检测过程中发生错误: {e}")
                time.sleep(1)  # 出错后等待一段时间再继续
    
    finally:
        # 确保在退出时释放资源
        with stream_locks[camera_id]:
            release_video_stream(camera_id)
        
        print(f"摄像头 {camera_id} YOLO识别已停止")

def check_yolo_timeout():
    """检查所有摄像头的YOLO是否需要超时关闭"""
    while True:
        time.sleep(1)  # 每秒检查一次
        
        for camera_id in yolo_status:
            with yolo_locks[camera_id]:
                if (yolo_status[camera_id]["running"] and 
                    yolo_status[camera_id]["last_detection_time"] > 0):
                    current_time = time.time()
                    last_detection = yolo_status[camera_id]["last_detection_time"]
                    time_since_last_detection = current_time - last_detection
                    
                    if time_since_last_detection > person_detection_timeout:
                        print(f"摄像头 {camera_id} 已超过{person_detection_timeout}秒未检测到人，自动停止YOLO识别")
                        yolo_status[camera_id]["running"] = False

def read_from_fifo():
    """读取FIFO管道内容并根据命令启动相应的YOLO检测"""
    # 存储YOLO线程
    yolo_threads = {
        "cam1": None,
        "cam2": None
    }
    
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
                
                # 持续读取FIFO管道内容
                while True:
                    try:
                        # 尝试读取数据
                        data = fifo.read()
                        if data:
                            data_str = data.decode('utf-8', 'ignore')
                            print(f"Received: {data_str}")
                            
                            # 处理摄像头1命令
                            if "leida_cam1" in data_str:
                                with yolo_locks["cam1"]:
                                    if not yolo_status["cam1"]["running"]:
                                        yolo_status["cam1"]["running"] = True
                                        yolo_status["cam1"]["last_detection_time"] = time.time()
                                        
                                        # 启动摄像头1的YOLO识别线程
                                        if yolo_threads["cam1"] is not None and yolo_threads["cam1"].is_alive():
                                            print("等待摄像头1旧的YOLO线程结束...")
                                            yolo_threads["cam1"].join(timeout=2)
                                        
                                        yolo_threads["cam1"] = threading.Thread(target=run_yolo_detection, args=("cam1",))
                                        yolo_threads["cam1"].daemon = True
                                        yolo_threads["cam1"].start()
                                    else:
                                        print("摄像头1的YOLO识别已在运行中")
                            
                            # 处理摄像头2命令
                            elif "leida_cam2" in data_str:
                                with yolo_locks["cam2"]:
                                    if not yolo_status["cam2"]["running"]:
                                        yolo_status["cam2"]["running"] = True
                                        yolo_status["cam2"]["last_detection_time"] = time.time()
                                        
                                        # 启动摄像头2的YOLO识别线程
                                        if yolo_threads["cam2"] is not None and yolo_threads["cam2"].is_alive():
                                            print("等待摄像头2旧的YOLO线程结束...")
                                            yolo_threads["cam2"].join(timeout=2)
                                        
                                        yolo_threads["cam2"] = threading.Thread(target=run_yolo_detection, args=("cam2",))
                                        yolo_threads["cam2"].daemon = True
                                        yolo_threads["cam2"].start()
                                    else:
                                        print("摄像头2的YOLO识别已在运行中")
                            
                            # 处理同时启动两个摄像头的命令
                            elif "leida_" in data_str:
                                for cam_id in ["cam1", "cam2"]:
                                    with yolo_locks[cam_id]:
                                        if not yolo_status[cam_id]["running"]:
                                            yolo_status[cam_id]["running"] = True
                                            yolo_status[cam_id]["last_detection_time"] = time.time()
                                            
                                            # 启动对应摄像头的YOLO识别线程
                                            if yolo_threads[cam_id] is not None and yolo_threads[cam_id].is_alive():
                                                print(f"等待摄像头{cam_id}旧的YOLO线程结束...")
                                                yolo_threads[cam_id].join(timeout=2)
                                            
                                            yolo_threads[cam_id] = threading.Thread(target=run_yolo_detection, args=(cam_id,))
                                            yolo_threads[cam_id].daemon = True
                                            yolo_threads[cam_id].start()
                                        else:
                                            print(f"摄像头{cam_id}的YOLO识别已在运行中")
                            
                            # 处理普通的leida_命令（默认启动摄像头1）
                            elif "leida_" in data_str and not any(x in data_str for x in ["cam1", "cam2", "all"]):
                                with yolo_locks["cam1"]:
                                    if not yolo_status["cam1"]["running"]:
                                        yolo_status["cam1"]["running"] = True
                                        yolo_status["cam1"]["last_detection_time"] = time.time()
                                        
                                        # 启动摄像头1的YOLO识别线程
                                        if yolo_threads["cam1"] is not None and yolo_threads["cam1"].is_alive():
                                            print("等待摄像头1旧的YOLO线程结束...")
                                            yolo_threads["cam1"].join(timeout=2)
                                        
                                        yolo_threads["cam1"] = threading.Thread(target=run_yolo_detection, args=("cam1",))
                                        yolo_threads["cam1"].daemon = True
                                        yolo_threads["cam1"].start()
                                    else:
                                        print("摄像头1的YOLO识别已在运行中")
                            
                            # 处理停止命令
                            elif "stop_cam1" in data_str:
                                with yolo_locks["cam1"]:
                                    if yolo_status["cam1"]["running"]:
                                        yolo_status["cam1"]["running"] = False
                                        print("手动停止摄像头1的YOLO识别")
                            
                            elif "stop_cam2" in data_str:
                                with yolo_locks["cam2"]:
                                    if yolo_status["cam2"]["running"]:
                                        yolo_status["cam2"]["running"] = False
                                        print("手动停止摄像头2的YOLO识别")
                            
                            elif "stop_all" in data_str or "stop_yolo" in data_str:
                                for cam_id in ["cam1", "cam2"]:
                                    with yolo_locks[cam_id]:
                                        if yolo_status[cam_id]["running"]:
                                            yolo_status[cam_id]["running"] = False
                                            print(f"手动停止摄像头{cam_id}的YOLO识别")
                        
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
    """将检测结果写入FIFO管道"""
    # 记录上次是否发送了person消息
    last_sent = {
        "cam1": False,
        "cam2": False
    }
    
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
                
                while True:
                    try:
                        # 检查每个摄像头是否检测到人
                        for cam_id in yolo_status:
                            with yolo_locks[cam_id]:
                                local_person_detected = yolo_status[cam_id]["person_detected"]
                                if local_person_detected:
                                    yolo_status[cam_id]["person_detected"] = False  # 重置检测标志
                            
                            if local_person_detected:
                                if not last_sent[cam_id]:  # 只有当状态改变时才发送
                                    message = f"person_{cam_id}\0"
                                    fifo1.write(message.encode('utf-8'))
                                    fifo1.flush()  # 确保数据被写入
                                    print(f"Sent: {message}")
                                    last_sent[cam_id] = True
                        else:
                                if last_sent[cam_id]:  # 状态改变，重置标志
                                    last_sent[cam_id] = False
                        
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
        for cam_id in cameras:
            with stream_locks[cam_id]:
                release_video_stream(cam_id)