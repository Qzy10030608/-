from flask import Flask, request, jsonify
import cv2
import os
import time
from threading import Thread
from queue import Queue
import requests

# 初始化 Flask 应用
app = Flask(__name__)

# 配置文件保存路径
UPLOAD_FOLDER = 'C:\\Users\\user\\Pictures\\Screenshots'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ESP32-CAM 视频流地址
url = "http://192.168.0.6:81/stream"  # 替换为实际 ESP32-CAM 地址
cap = cv2.VideoCapture(url)  # 打开视频流

# 加载 OpenCV 的人脸检测 Haar 模型
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# 检查视频流是否成功打开
if not cap.isOpened():
    print("无法打开视频流，请检查地址或摄像头状态！")
    exit()
else:
    print("视频流已成功打开")

# 初始化队列，用于保存最新视频帧
frame_queue = Queue(maxsize=1)

# 设置触发时间戳变量和间隔
last_trigger_time = 0
trigger_interval = 6  # 限制触发间隔为 6 秒

@app.route('/take_photo', methods=['GET'])
def take_photo():
    """
    接收 M5 的拍照指令，抓取视频帧并保存到服务器
    """
    print("收到 M5 的拍照请求")

    if frame_queue.empty():
        print("当前没有可用帧")
        return jsonify({"status": "error", "message": "没有可用视频帧"}), 500

    # 从队列中获取最新视频帧
    frame = frame_queue.get()

    # 保存图像文件
    timestamp = int(time.time())
    local_filename = os.path.join(UPLOAD_FOLDER, f"photo_{timestamp}.jpg")
    success = cv2.imwrite(local_filename, frame)

    if not success:
        print("保存照片失败")
        return jsonify({"status": "error", "message": "保存照片失败"}), 500

    print(f"照片已保存到本地: {local_filename}")

    # 模拟上传照片到远程服务器
    upload_url = "http://192.168.0.105:5001/upload_photo"  # 替换为服务器的上传地址
    with open(local_filename, 'rb') as f:
        response = requests.post(upload_url, files={'photo': f})

    if response.status_code == 200:
        print("照片上传成功")
        return jsonify({"status": "success", "message": "照片上传成功"}), 200
    else:
        print(f"照片上传失败: {response.status_code}")
        return jsonify({"status": "error", "message": "照片上传失败"}), 500

def detect_faces():
    """
    人脸检测主函数，检测到人脸后通知 M5 激活
    """
    global last_trigger_time

    try:
        # 从视频流中读取一帧
        ret, frame = cap.read()
        if not ret:
            print("无法抓取视频帧，视频流可能已断开！")
            return None, []

        # 将最新帧放入队列
        if not frame_queue.full():
            frame_queue.put(frame)

        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 检测人脸
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        # 如果检测到人脸并超过触发间隔
        current_time = time.time()
        if len(faces) > 0 and current_time - last_trigger_time > trigger_interval:
            print("检测到人脸，激活 M5StickC Plus...")
            last_trigger_time = current_time

            # 向 M5StickC Plus 发送激活请求
            try:
                m5_url = "http://192.168.0.8/activate"  # 替换为 M5StickC Plus 的 IP 地址
                response = requests.get(m5_url)
                if response.status_code == 200:
                    print("激活请求成功")
                else:
                    print(f"激活请求失败，状态码: {response.status_code}")
            except Exception as e:
                print(f"激活请求失败: {e}")

        return frame, faces
    except Exception as e:
        print(f"检测过程中出现异常: {e}")
        return None, []

def main_loop():
    """
    主循环：检测人脸并显示视频流
    """
    while True:
        frame, faces = detect_faces()

        if frame is not None:
            # 在视频帧上绘制人脸框
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # 显示处理后的视频流
            cv2.imshow("ESP32-CAM 人脸检测", frame)

        # 按下 'q' 键退出程序
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 释放视频流资源
    cap.release()
    cv2.destroyAllWindows()

def flask_thread():
    """
    启动 Flask 服务器
    """
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    # 启动 Flask 服务器线程
    server_thread = Thread(target=flask_thread)
    server_thread.daemon = True
    server_thread.start()

    # 运行人脸检测主循环
    main_loop()
