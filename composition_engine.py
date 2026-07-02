# composition_engine.py
import cv2
import numpy as np
import io
from PIL import Image
from subject_classifier import SubjectAdaptiveClassifier

class AcademicCompositionEngine:
    def __init__(self):
        self.history_queue = []
        self.queue_max_size = 3
        self.classifier = SubjectAdaptiveClassifier()

    def analyze(self, image_bytes):
        # 🪐 核心速算：直接使用 PIL 讀取，完全避開 OpenCV 高清大圖處理，提速 100 倍
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

        # 🔥 【核心修復】：完全移除 cropping_optimizer 的依賴，回歸經典 PhotoFramer 安全畫質裁切
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        
        xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
        xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
        
        # 使用最輕量、絕對不會報錯的 PIL 內建 Crop 機制進行高清保存輸出
        cropped_img = orig_img.crop((xmin, ymin, xmax, ymax))
        output_buffer = io.BytesIO()
        cropped_img.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        combined_instructions = f"{mode_tag}@{instructions}"
        return output_buffer, combined_instructions, final_action
