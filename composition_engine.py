# composition_engine.py
import cv2
import numpy as np
import io
from subject_classifier import SubjectAdaptiveClassifier
# 🔥 引入剛剛新蓋的獨立美學裁切優化器
from cropping_optimizer import AestheticCroppingOptimizer

class AcademicCompositionEngine:
    def __init__(self):
        self.history_queue = []
        self.queue_max_size = 3
        self.classifier = SubjectAdaptiveClassifier()
        # 實實例化優化器
        self.optimizer = AestheticCroppingOptimizer()

    def analyze(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, "圖片解析失敗", "hold"
        
        h, w, _ = img.shape
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # 呼叫大腦感知，拿回即時引導純指令
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

        # ─── 按下快門後的精華美學處理 ───
        # 預設基礎網格交點中心
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        
        # 🔥 【核心串聯】：調用專職優化器進行動態不對稱留白偏置與天然框架鎖定
        xmin, ymin, xmax, ymax = self.optimizer.optimize_crop_box(img, edges, gray, cx, cy)
        
        # 執行高級感輸出裁切
        cropped = img[ymin:ymax, xmin:xmax]
        _, img_encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        
        combined_instructions = f"{mode_tag}@{instructions}"
        return io.BytesIO(img_encoded.tobytes()), combined_instructions, final_action
