# 双摄像头YOLO目标检测系统

基于FIFO管道通信的双USB摄像头YOLO目标检测系统，可以独立控制两个摄像头进行人员检测，并通过管道通信与其他程序交互。

## 功能特点

- 支持两个USB摄像头（/dev/video1和/dev/video3）同时或独立进行YOLO目标检测
- 使用FIFO管道进行进程间通信，便于与其他程序集成
- 自动管理摄像头资源，确保资源正确释放
- 支持超时自动关闭检测，节省系统资源
- 检测到人员时自动发送通知
- 支持多种控制命令，灵活控制检测行为

## 安装依赖

```bash
# 安装OpenCV
pip install opencv-python

# 安装Ultralytics YOLO
pip install ultralytics

# 其他依赖库
pip install numpy
```

## 文件说明

- `yolo_fifo_2cam.py`: 主程序，实现双摄像头YOLO检测功能
- `analog_signal.py`: 模拟信号发生器，用于测试系统

## 使用方法

### 1. 启动YOLO检测程序

```bash
python3 yolo_fifo_2cam.py
```

### 2. 通过FIFO管道发送控制命令

可以使用以下命令通过FIFO管道控制YOLO检测：

```bash
# 启动摄像头1的YOLO检测
echo "leida_cam1" > /home/cat/leida_test/Z_pavo2__test/send_PYTHON

# 启动摄像头2的YOLO检测
echo "leida_cam2" > /home/cat/leida_test/Z_pavo2__test/send_PYTHON

# 同时启动两个摄像头的YOLO检测
echo "leida_" > /home/cat/leida_test/Z_pavo2__test/send_PYTHON

# 停止摄像头1的YOLO检测
echo "stop_cam1" > /home/cat/leida_test/Z_pavo2__test/send_PYTHON

# 停止摄像头2的YOLO检测
echo "stop_cam2" > /home/cat/leida_test/Z_pavo2__test/send_PYTHON

# 停止所有摄像头的YOLO检测
echo "stop_yolo" > /home/cat/leida_test/Z_pavo2__test/send_PYTHON
```

### 3. 接收检测结果

程序检测到人员时，会向FIFO管道发送通知：

```bash
# 监听检测结果
cat /home/cat/leida_test/Z_pavo2__test/rece_PYTHON
```

检测到人员时，会收到类似`person_cam1`或`person_cam2`的消息，分别表示摄像头1或摄像头2检测到人员。

## 自动超时关闭

系统设计了自动超时关闭机制：如果连续10秒没有检测到人员，YOLO检测会自动停止，直到收到新的启动命令。这有助于节省系统资源。

## 技术实现

- 使用OpenCV读取摄像头视频流
- 使用Ultralytics YOLO进行目标检测
- 使用多线程实现并行处理
- 使用FIFO管道实现进程间通信
- 使用线程锁保证线程安全

## 注意事项

1. 确保系统已连接USB摄像头，并且设备路径正确（/dev/video1和/dev/video3）
2. 确保FIFO管道目录存在且有正确的读写权限
3. 程序需要加载YOLO模型文件"yolo11n_rknn_model"，请确保该文件存在
4. 程序会自动创建FIFO管道，但可能需要管理员权限

## 故障排除

- 如果摄像头无法打开，请检查设备路径和权限
- 如果FIFO管道通信失败，请检查目录权限和管道是否存在
- 如果YOLO模型加载失败，请确认模型文件路径是否正确
- 如果检测性能不佳，可以调整摄像头参数（分辨率、帧率等）