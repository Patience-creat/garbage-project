from ultralytics import YOLO
import cv2

# 加载YOLOv8模型
model = YOLO("yolov8n.pt")

# 打开摄像头
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("打不开摄像头")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # AI识别
    results = model(frame)

    # 画框+显示
    annotated = results[0].plot()
    cv2.imshow("AI 识别窗口", annotated)

    # 按 q 退出
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()