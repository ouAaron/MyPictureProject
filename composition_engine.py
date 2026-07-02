# composition_engine.py
import cv2
import numpy as np
import io
from subject_classifier import SubjectAdaptiveClassifier

class AcademicCompositionEngine:
    def __init__(self):
        self.history_queue = []
        self.queue_max_size = 3
        self.classifier = SubjectAdaptiveClassifier()

    def analyze(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, "圖片解析失敗", "hold"
        
        h, w, _ = img.shape
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # 拿回帶有模式標籤的複合指令
        raw_result, raw_action = self.classifier.detect_and_align(img, edges, gray)
        mode_tag, instructions = raw_result.split('|')

        # 時序平滑濾波（防跳針）
        self.history_queue.append(raw_action)
        if len(self.history_queue) > self.queue_max_size:
            self.history_queue.pop(0)
        
        final_action = max(set(self.history_queue), key=self.history_queue.count)
        
        if final_action == "perfect" and "完美" not in instructions and "達標" not in instructions:
            instructions = "構圖美學結構趨於穩定，畫面幾何平衡合格，請按下快門"

        # 幾何裁切
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
        xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
        
        cropped = img[ymin:ymax, xmin:xmax]
        _, img_encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        
        # 將 mode_tag 塞進 instructions 字串前段，用 ＠ 符號隔開，讓前端 app.py 好解析
        combined_instructions = f"{mode_tag}@{instructions}"
        return io.BytesIO(img_encoded.tobytes()), combined_instructions, final_action
