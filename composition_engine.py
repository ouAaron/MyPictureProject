# composition_engine.py
import io
from PIL import Image
from subject_classifier import SubjectAdaptiveClassifier

class AcademicCompositionEngine:
    def __init__(self):
        self.history_queue = []
        self.queue_max_size = 3
        self.classifier = SubjectAdaptiveClassifier()

    def analyze(self, image_bytes):
        try:
            orig_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except:
            return None, "圖片解析失敗", "hold"
        
        w, h = orig_img.size
        
        # 呼叫高速大腦，一進去就給出引導意見
        raw_result, raw_action = self.classifier.detect_and_align_fast(orig_img)
        
        # 🔥 【核心校準修復】：如果帶有舊標籤，直接過濾掉，只留下純粹的指令字串
        instructions = raw_result.split('@')[1] if '@' in raw_result else raw_result

        # 時序平滑濾波（防跳針）
        self.history_queue.append(raw_action)
        if len(self.history_queue) > self.queue_max_size:
            self.history_queue.pop(0)
        
        final_action = max(set(self.history_queue), key=self.history_queue.count)
        
        if final_action == "perfect" and "請" not in instructions and "退" not in instructions:
            instructions = "畫面結構穩定平衡，請直接按下快門"

        # 經典原生 PhotoFramer 安全快門裁切機制
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        
        xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
        xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
        
        cropped_img = orig_img.crop((xmin, ymin, xmax, ymax))
        output_buffer = io.BytesIO()
        cropped_img.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        # 🪐 直接回傳純字串給前端，絕不附加任何雜質！
        return output_buffer, instructions, final_action
