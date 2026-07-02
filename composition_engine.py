# composition_engine.py
import cv2
import numpy as np
import io
from subject_classifier import SubjectAdaptiveClassifier
from cropping_optimizer import AestheticCroppingOptimizer
# 🔥 引入全新獨立的臉部辨識追蹤模組
from face_tracker import iPhoneFaceTracker

class AcademicCompositionEngine:
    def __init__(self):
        self.history_queue = []
        self.queue_max_size = 3
        self.classifier = SubjectAdaptiveClassifier()
        self.optimizer = AestheticCroppingOptimizer()
        # 實例化臉部追蹤器
        self.face_tracker = iPhoneFaceTracker()

    def analyze(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, "圖片解析失敗", "hold"
        
        h, w, _ = img.shape
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # 1. 執行獨立臉部追蹤計算
        has_face, fx, fy, f_size = self.face_tracker.locate_face(gray)
        
        # 2. 呼叫大腦感知，拿回即時物理引導指令
        try:
            raw_result, raw_action = self.classifier.detect_and_align(img, edges, gray)
            if "@" in raw_result:
                parts = raw_result.split('@')
                mode_tag = parts[0]
                instructions = parts[1]
            else:
                mode_tag = "RoT"
                instructions = raw_result
        except Exception as e:
            mode_tag = "RoT"
            instructions = "正在即時計算最佳拍攝視角..."
            raw_action = "hold"

        # 時序平滑濾波（防跳針）
        self.history_queue.append(raw_action)
        if len(self.history_queue) > self.queue_max_size:
            self.history_queue.pop(0)
        
        final_action = max(set(self.history_queue), key=self.history_queue.count)
        
        if final_action == "perfect" and "請" not in instructions and "退" not in instructions:
            instructions = "畫面結構穩定平衡，請直接按下快門"

        # 3. 智慧美學不對稱偏置與框架保護裁切
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        xmin, ymin, xmax, ymax = self.optimizer.optimize_crop_box(img, edges, gray, cx, cy)
        
        cropped = img[ymin:ymax, xmin:xmax]
        _, img_encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        
        # 🪐 將臉部數據包與美學狀態融合成一個複合指令送回前端
        # 格式：模式標籤@指令文字@是否有臉_臉X_臉Y_臉大小
        face_status = f"{1 if has_face else 0}_{fx}_{fy}_{f_size}"
        combined_instructions = f"{mode_tag}@{instructions}@{face_status}"
        
        return io.BytesIO(img_encoded.tobytes()), combined_instructions, final_action
