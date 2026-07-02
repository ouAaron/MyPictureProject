# composition_engine.py
import cv2
import numpy as np
import io
from PIL import Image
from subject_classifier import SubjectAdaptiveClassifier
from cropping_optimizer import AestheticCroppingOptimizer

class AcademicCompositionEngine:
    def __init__(self):
        self.history_queue = []
        self.queue_max_size = 3
        self.classifier = SubjectAdaptiveClassifier()
        self.optimizer = AestheticCroppingOptimizer()

    def analyze(self, image_bytes):
        # 🪐 核心速算：直接使用 PIL 讀取，完全避開 OpenCV 高清大圖處理
        try:
            orig_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except:
            return None, "圖片解析失敗", "hold"
        
        w, h = orig_img.size
        
        # 呼叫极速大腦，一進去就給出引導意見 (零延遲)
        raw_result, raw_action = self.classifier.detect_and_align_fast(orig_img)
        mode_tag, instructions = raw_result.split('@')

        # 時序平滑濾波（防跳針）
        self.history_queue.append(raw_action)
        if len(self.history_queue) > self.queue_max_size:
            self.history_queue.pop(0)
        
        final_action = max(set(self.history_queue), key=self.history_queue.count)
        
        if final_action == "perfect" and "請" not in instructions and "退" not in instructions:
            instructions = "畫面結構穩定平衡，請直接按下快門"

        # 3. 智慧美學裁切（只有快門按下時，才調用大圖進行不對稱留白裁切輸出）
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        
        img_np = np.array(orig_img)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        gray_small = cv2.resize(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY), (160, 120), interpolation=cv2.INTER_AREA)
        edges_small = cv2.Canny(cv2.GaussianBlur(gray_small, (3, 3), 0), 40, 120)
        
        xmin, ymin, xmax, ymax = self.optimizer.optimize_crop_box(img_bgr, edges_small, gray_small, cx, cy)
        
        # 還原到真實大圖座標
        scale_x = w / 160
        scale_y = h / 120
        xmin_real, ymin_real = int(xmin * scale_x), int(ymin * scale_y)
        xmax_real, ymax_real = int(xmax * scale_x), int(ymax * scale_y)
        
        cropped = img_bgr[ymin_real:ymax_real, xmin_real:xmax_real]
        _, img_encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        
        combined_instructions = f"{mode_tag}@{instructions}"
        return io.BytesIO(img_encoded.tobytes()), combined_instructions, final_action
