# composition_engine.py
import cv2
import numpy as np
import io
# 🔥 引入剛剛新蓋的獨立偵測模組
from subject_classifier import SubjectAdaptiveClassifier

class AcademicCompositionEngine:
    def __init__(self):
        self.history_queue = []
        self.queue_max_size = 3
        # 實例化偵測器
        self.classifier = SubjectAdaptiveClassifier()

    def analyze(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, "圖片解析失敗", "hold"
        
        h, w, _ = img.shape
        
        # 基礎邊緣計算
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # 🔥 【核心串聯】：直接將影像丟給專職分類器，拿回清晰的動作引導指令
        instructions, raw_action = self.classifier.detect_and_align(img, edges, gray)

        # 時序平滑濾波（防跳針）
        self.history_queue.append(raw_action)
        if len(self.history_queue) > self.queue_max_size:
            self.history_queue.pop(0)
        
        final_action = max(set(self.history_queue), key=self.history_queue.count)
        
        if final_action == "perfect" and "完美" not in instructions:
            instructions = "美學結構已趨於穩定，畫面幾何平衡合格，請按下快門"

        # 智慧美學裁切優化
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
        xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
        
        cropped = img[ymin:ymax, xmin:xmax]
        _, img_encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        return io.BytesIO(img_encoded.tobytes()), instructions, final_action
