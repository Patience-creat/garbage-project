"""
多线程检测引擎 — 在后台线程运行 YOLO 推理，不阻塞 UI
"""
import time
import cv2
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QMutexLocker


class DetectionWorker(QObject):
    """YOLO 推理工作器（运行在 QThread 中）

    Signals:
        result_ready: (frame_with_boxes: np.ndarray,
                       detections: list[(class_name, confidence)])
        fps_updated: (fps: float)
        status_message: (msg: str)
        camera_error: (msg: str)
        finished: ()
    """

    result_ready = pyqtSignal(object, list)
    fps_updated = pyqtSignal(float)
    status_message = pyqtSignal(str)
    camera_error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self._mutex = QMutex()
        self._running = False
        self._mode = None          # "camera", "image", "video"
        self._image_path = None
        self._video_path = None
        self._frame = None
        self._conf_threshold = 0.3
        self._device = "cpu"      # 强制 CPU，与模型加载一致
        self._camera_id = 0

    # ── 属性设置 ──

    def set_conf_threshold(self, conf):
        self._conf_threshold = conf

    def set_device(self, device):
        self._device = device

    # ── 摄像头模式 ──

    def start_camera(self, camera_id=0):
        with QMutexLocker(self._mutex):
            self._running = True
            self._mode = "camera"
            self._camera_id = camera_id

    # ── 图片模式 ──

    def start_image(self, image_path):
        self._image_path = image_path
        with QMutexLocker(self._mutex):
            self._running = True
            self._mode = "image"

    # ── 停止 ──

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False

    def is_running(self):
        with QMutexLocker(self._mutex):
            return self._running

    # ── 主循环 ──

    def run(self):
        """主工作循环 — 在 QThread 中运行"""
        self.status_message.emit("准备就绪")

        try:
            if self._mode == "camera":
                self._run_camera()
            elif self._mode == "image":
                self._run_image()
            else:
                self.status_message.emit("未知模式")
        except Exception as e:
            self.camera_error.emit(f"检测错误: {str(e)}")
        finally:
            self.finished.emit()

    def _run_camera(self):
        """摄像头实时检测循环（支持自动尝试多个摄像头索引）"""
        # 尝试多个摄像头索引（0~3）
        cap = None
        for cam_id in range(4):
            cap = cv2.VideoCapture(cam_id)
            if cap.isOpened():
                self._camera_id = cam_id
                self.status_message.emit(f"使用摄像头 #{cam_id}")
                break
            cap.release()
            cap = None

        if cap is None:
            self.camera_error.emit("无法打开摄像头，请检查设备连接（是否被其他应用占用？）")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.status_message.emit("摄像头已开启")
        fps_counter = _FPSCounter()

        while self.is_running():
            ret, frame = cap.read()
            if not ret:
                self.camera_error.emit("摄像头读取失败")
                break

            # 推理
            try:
                results = self.model(frame, conf=self._conf_threshold, device=self._device, verbose=False)
                annotated = results[0].plot()
                detections = self._extract_detections(results[0])
            except Exception as e:
                self.camera_error.emit(f"推理错误: {str(e)}")
                break

            # 统计
            fps_counter.tick()
            current_fps = fps_counter.fps
            self.fps_updated.emit(current_fps)

            # 发送结果
            self.result_ready.emit(annotated, detections)

            # 控制帧率 ~30fps
            elapsed = fps_counter.elapsed_since_last()
            sleep_time = max(0, 1.0 / 30 - elapsed)
            if sleep_time > 0:
                QThread.msleep(int(sleep_time * 1000))

        cap.release()
        self.status_message.emit("摄像头已停止")

    def _run_image(self):
        """单张图片检测"""
        if not self._image_path:
            self.status_message.emit("未选择图片")
            return

        self.status_message.emit("正在检测图片...")
        QThread.msleep(100)  # 让 UI 有时间更新状态

        frame = cv2.imread(self._image_path)
        if frame is None:
            self.camera_error.emit(f"无法读取图片: {self._image_path}")
            return

        results = self.model(frame, conf=self._conf_threshold, device=self._device, verbose=False)
        annotated = results[0].plot()
        detections = self._extract_detections(results[0])

        self.result_ready.emit(annotated, detections)
        self.status_message.emit("图片检测完成")

    def _extract_detections(self, result):
        """从 YOLO 结果中提取 (类名, 置信度) 列表"""
        detections = []
        if result.boxes is not None:
            for box in result.boxes:
                cls_id = int(box.cls)
                cls_name = self.model.names[cls_id]
                conf = float(box.conf)
                detections.append((cls_name, conf))
        return detections


class _FPSCounter:
    """简易 FPS 计数器"""

    def __init__(self):
        self._last_time = time.time()
        self._fps = 0.0
        self._count = 0
        self._accum = 0.0

    def tick(self):
        now = time.time()
        dt = now - self._last_time
        self._last_time = now
        self._accum += dt
        self._count += 1
        if self._accum >= 0.5:  # 每0.5秒更新一次FPS
            self._fps = self._count / self._accum
            self._count = 0
            self._accum = 0.0

    @property
    def fps(self):
        return self._fps

    def elapsed_since_last(self):
        return time.time() - self._last_time
