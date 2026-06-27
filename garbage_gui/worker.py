"""
多线程检测引擎 — 在后台线程运行 YOLO 推理，不阻塞 UI
"""
import time
import cv2
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QMutexLocker
from .config import auto_device


class DetectionWorker(QObject):
    """YOLO 推理工作器（运行在 QThread 中）"""

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
        self._mode = None
        self._image_path = None
        self._conf_threshold = 0.25
        self._device = auto_device()
        self._camera_id = 0

    def set_conf_threshold(self, conf):
        self._conf_threshold = conf

    def set_device(self, device):
        self._device = device

    def start_camera(self, camera_id=0):
        with QMutexLocker(self._mutex):
            self._running = True
            self._mode = "camera"
            self._camera_id = camera_id

    def start_image(self, image_path):
        self._image_path = image_path
        with QMutexLocker(self._mutex):
            self._running = True
            self._mode = "image"

    def stop(self):
        with QMutexLocker(self._mutex):
            self._running = False

    def is_running(self):
        with QMutexLocker(self._mutex):
            return self._running

    def run(self):
        self.status_message.emit("准备就绪")
        try:
            if self._mode == "camera":
                self._run_camera()
            elif self._mode == "image":
                self._run_image()
        except Exception as e:
            self.camera_error.emit(f"检测错误: {str(e)}")
        finally:
            self.finished.emit()

    # ── 摄像头模式 ──

    def _run_camera(self):
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
            self.camera_error.emit("无法打开摄像头，请检查设备连接")
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
            try:
                results = self.model(frame, conf=self._conf_threshold, device=self._device, verbose=False)
                annotated = results[0].plot()
                detections = self._extract_detections(results[0])
            except Exception as e:
                self.camera_error.emit(f"推理错误: {str(e)}")
                break

            fps_counter.tick()
            self.fps_updated.emit(fps_counter.fps)
            self.result_ready.emit(annotated, detections)

            elapsed = fps_counter.elapsed_since_last()
            sleep_time = max(0, 1.0 / 30 - elapsed)
            if sleep_time > 0:
                QThread.msleep(int(sleep_time * 1000))

        cap.release()
        self.status_message.emit("摄像头已停止")

    # ── 图片模式：单次检测，框才能对准 ──

    def _run_image(self):
        if not self._image_path:
            self.status_message.emit("未选择图片")
            return

        self.status_message.emit("正在检测图片...")
        QThread.msleep(50)

        frame = cv2.imread(self._image_path)
        if frame is None:
            self.camera_error.emit(f"无法读取图片: {self._image_path}")
            return

        start_time = time.time()
        results = self.model(frame, conf=self._conf_threshold, device=self._device, verbose=False)
        annotated = results[0].plot()
        detections = self._extract_detections(results[0])
        elapsed = time.time() - start_time

        processing_speed = 1.0 / elapsed if elapsed > 0 else 0
        self.fps_updated.emit(processing_speed)
        self.result_ready.emit(annotated, detections)
        self.status_message.emit(f"图片检测完成 ({elapsed*1000:.0f}ms)")

    def _extract_detections(self, result):
        detections = []
        if result.boxes is not None:
            for box in result.boxes:
                cls_id = int(box.cls)
                cls_name = self.model.names[cls_id]
                detections.append((cls_name, float(box.conf)))
        return detections


class _FPSCounter:
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
        if self._accum >= 0.5:
            self._fps = self._count / self._accum
            self._count = 0
            self._accum = 0.0

    @property
    def fps(self):
        return self._fps

    def elapsed_since_last(self):
        return time.time() - self._last_time
