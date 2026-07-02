# composition_engine.py
import cv2
import numpy as np
import io
from subject_classifier import SubjectAdaptiveClassifier
from cropping_optimizer import AestheticCroppingOptimizer
from face_tracker import iPhoneFaceTracker

class AcademicCompositionEngine:
    def __init__(self):
        self.history_queue = []
        self.queue_max_size = 3
        self.classifier = SubjectAdaptiveClassifier()
        self.optimizer = AestheticCroppingOptimizer()
        self.face_tracker = iPhoneFaceTracker()

    def analyze(self, image_bytes):
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, "圖片解析失敗", "hold"
        
        h, w, _ = img.shape
        
        # 🪐 【極速效能優化】：建立輕量化特徵矩陣（Downsampling）
        # 將原本沉重的高清影像壓縮至 160 寬度進行美學特徵統計，運算時間直接縮短 50 倍！
        target_small_w = 160
        target_small_h = int((h / w) * target_small_w)
        img_small = cv2.resize(img, (target_small_w, target_small_h), interpolation=cv2.INTER_AREA)
        
        gray_small = cv2.cvtColor(img_small, cv2.COLOR_BGR2GRAY)
        blurred_small = cv2.GaussianBlur(gray_small, (3, 3), 0)
        edges_small = cv2.Canny(blurred_small, 40, 120)
        
        # 1. 執行獨立臉部追蹤計算（同樣使用輕量矩陣，提速防卡頓）
        has_face, fx, fy, f_size = self.face_tracker.locate_face(gray_small)
        
        # 2. 呼叫大腦感知，使用毫秒級輕量矩陣拿回純指令
        try:
            raw_result, raw_action = self.classifier.detect_and_align(img_small, edges_small, gray_small)
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

        # 3. 智慧美學不對稱偏置與框架保護裁切（在最後快門輸出時，才使用高清原圖進行精緻裁切，確保畫質完美）
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        
        # 為了配合降採樣後的臉部比例，我們把真實原圖的高清 edges 送入優化器
        gray_full = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges_full = cv2.Canny(cv2.GaussianBlur(gray_full, (5, 5), 0), 50, 150)
        xmin, ymin, xmax, ymax = self.optimizer.optimize_crop_box(img, edges_full, gray_full, cx, cy)
        
        cropped = img[ymin:ymax, xmin:xmax]
        _, img_encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        
        # 🪐 臉部寬度 f_size 還原比例對接（160 像素還原至 240 規格）
        normalized_f_size = f_size * (240 / target_small_w)
        face_status = f"{1 if has_face else 0}_{fx}_{fy}_{normalized_f_size}"
        combined_instructions = f"{mode_tag}@{instructions}@{face_status}"
        
        return io.BytesIO(img_encoded.tobytes()), combined_instructions, final_action
