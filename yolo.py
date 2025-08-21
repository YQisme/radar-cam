import cv2
from ultralytics import YOLO
# 设置摄像头设备索引
source = "rtsp://admin:scyzkj123456@192.168.0.2:554/h264/ch1/main/av_stream"

# 加载预训练的 YOLO 模型
model = YOLO("yolo11n.pt")
results = model(source)
