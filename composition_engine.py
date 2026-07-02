# composition_engine.py
import cv2
import numpy as np
import io
from PIL import Image
from subject_classifier import SubjectAdaptiveClassifier
from cropping_optimizer import AestheticCroppingOptimizer

class AcademicCompositionEngine:
    def __init__(self):
        self.classifier = SubjectAdaptiveClassifier()
        self.optimizer = AestheticCroppingOptimizer()

    def analyze(self, image_bytes):
        try:
            orig_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except:
            return None, "圖片解析失敗", "hold"
        
        w, h = orig_img.size
        img_np = np.array(orig_img)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        
        # 🪐 建立輕量化小圖矩陣供大腦瞬間分析
        gray_small = cv2.resize(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY), (160, 120), interpolation=cv2.INTER_AREA)
        edges_small = cv2.Canny(cv2.GaussianBlur(gray_small, (3, 3), 0), 40, 120)
        
        # 呼叫高速大腦做出裁切決策
        raw_result, raw_action = self.classifier.detect_and_align_fast(orig_img)
        
        # 呼叫 cropping_optimizer 進行不對稱留白與幾何保護裁切
        cx = w // 3 if raw_action == "left" else ((2 * w) // 3 if raw_action == "right" else w // 2)
        cy = h // 2
        
        xmin, ymin, xmax, ymax = self.optimizer.optimize_crop_box(img_bgr, edges_small, gray_small, cx, cy)
        
        # 還原到真實高清大圖座標
        scale_x = w / 160
        scale_y = h / 120
        xmin_real, ymin_real = int(xmin * scale_x), int(ymin * scale_y)
        xmax_real, ymax_real = int(xmax * scale_x), int(ymax * scale_y)
        
        cropped = img_bgr[ymin_real:ymax_real, xmin_real:ymax_real]
        _, img_encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        
        return io.BytesIO(img_encoded.tobytes()), "SUCCESS", raw_action
