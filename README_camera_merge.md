# 摄像头画面拼接推流工具

这个工具可以将两个摄像头的画面拼接后推流到MediaMTX服务器。

## 功能说明

- 从 `/dev/video1` 摄像头取左边70%的画面
- 从 `/dev/video3` 摄像头取右边70%的画面  
- 将两个画面水平拼接
- 推流到MediaMTX服务器

## 文件说明

1. `camera_merge_stream.sh` - Bash脚本版本
2. `camera_merge_stream.py` - Python脚本版本（推荐使用）

## 使用方法

### 方法1：使用Python脚本（推荐）

```bash
# 使用默认参数
python3 camera_merge_stream.py

# 自定义参数
python3 camera_merge_stream.py --video1 /dev/video1 --video3 /dev/video3 --url rtmp://localhost:1935/live/merged_cameras --width 1280 --height 720 --fps 30 --bitrate 2000k
```

### 方法2：使用Bash脚本

```bash
# 直接运行
./camera_merge_stream.sh
```

## 参数说明

- `--video1`: 第一个摄像头设备路径（默认：/dev/video1）
- `--video3`: 第三个摄像头设备路径（默认：/dev/video3）
- `--url`: 推流URL（默认：rtmp://localhost:1935/live/merged_cameras）
- `--width`: 输出宽度（默认：1280）
- `--height`: 输出高度（默认：720）
- `--fps`: 帧率（默认：30）
- `--bitrate`: 码率（默认：2000k）

## 前置条件

1. 确保摄像头设备存在：
   ```bash
   ls -la /dev/video*
   ```

2. 确保MediaMTX服务器正在运行：
   ```bash
   # 启动MediaMTX
   ./mediamtx
   ```

3. 确保安装了FFmpeg：
   ```bash
   ffmpeg -version
   ```

## 观看推流

推流开始后，可以通过以下方式观看：

1. 使用VLC播放器：
   ```
   rtmp://localhost:1935/live/merged_cameras
   ```

2. 使用浏览器访问MediaMTX Web界面：
   ```
   http://localhost:8888/live/merged_cameras/
   ```

## 故障排除

1. **摄像头设备不存在**：
   - 检查设备路径是否正确
   - 确保摄像头已正确连接

2. **FFmpeg执行失败**：
   - 检查FFmpeg是否已安装
   - 检查摄像头是否被其他程序占用

3. **推流连接失败**：
   - 检查MediaMTX服务器是否正在运行
   - 检查网络连接和端口设置

## 停止推流

按 `Ctrl+C` 停止推流。

## 技术细节

- 输入摄像头分辨率：640x480
- video1裁剪：左边70%（448像素）
- video3裁剪：右边70%（从192像素开始，448像素宽）
- 输出编码：H.264
- 推流协议：RTMP