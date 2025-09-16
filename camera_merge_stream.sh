#!/bin/bash

# 摄像头画面拼接推流脚本
# 功能：将/dev/video1左边70%和/dev/video3右边70%拼接后推流到MediaMTX

# 设置参数
VIDEO1_DEVICE="/dev/video1"
VIDEO3_DEVICE="/dev/video3"
STREAM_URL="rtmp://localhost:1935/live"  # MediaMTX推流地址
OUTPUT_WIDTH=1280
OUTPUT_HEIGHT=720
FPS=30

# 检查摄像头设备是否存在
if [ ! -e "$VIDEO1_DEVICE" ]; then
    echo "错误：摄像头设备 $VIDEO1_DEVICE 不存在"
    exit 1
fi

if [ ! -e "$VIDEO3_DEVICE" ]; then
    echo "错误：摄像头设备 $VIDEO3_DEVICE 不存在"
    exit 1
fi

echo "开始摄像头画面拼接推流..."
echo "视频1设备: $VIDEO1_DEVICE (左边70%)"
echo "视频3设备: $VIDEO3_DEVICE (右边70%)"
echo "推流地址: $STREAM_URL"
echo "输出分辨率: ${OUTPUT_WIDTH}x${OUTPUT_HEIGHT}"
echo "帧率: ${FPS}fps"
echo ""

# FFmpeg命令实现画面拼接和推流
ffmpeg \
    -f v4l2 -input_format mjpeg -video_size 640x480 -framerate $FPS -i "$VIDEO1_DEVICE" \
    -f v4l2 -input_format mjpeg -video_size 640x480 -framerate $FPS -i "$VIDEO3_DEVICE" \
    -filter_complex "
        [0:v]crop=320:480:0:0,scale=640:720[v1_cropped];
        [1:v]crop=320:480:192:0,scale=640:720[v3_cropped];
        [v1_cropped][v3_cropped]hstack=inputs=2[merged];
        [merged]scale=$OUTPUT_WIDTH:$OUTPUT_HEIGHT[output]
    " \
    -map "[output]" \
    -c:v libx264 \
    -preset ultrafast \
    -tune zerolatency \
    -b:v 2000k \
    -maxrate 2000k \
    -bufsize 4000k \
    -g 60 \
    -keyint_min 60 \
    -sc_threshold 0 \
    -f flv \
    "$STREAM_URL"

echo "推流结束"
