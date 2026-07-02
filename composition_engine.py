# composition_engine.py
from PIL import Image, ImageStat
import io

class AcademicCompositionEngine:
    def __init__(self):
        # 嚴格且靈敏的美學失衡門檻 (5%)
        self.imbalance_threshold = 1.05   
        self.history_queue = []
        self.queue_max_size = 3 # 3幀平滑，兼顧即時反應與防抖

    def analyze(self, image_bytes):
        try:
            orig_img = Image.open(io.BytesIO(image_bytes))
            orig_img = orig_img.convert("RGB")
        except:
            return None, "圖片解析失敗", "hold"
        
        w, h = orig_img.size
        
        # 空間幾何三分區域切片（利用 PIL 內建矩陣，速度極快）
        left_third = orig_img.crop((0, 0, w // 3, h))
        right_third = orig_img.crop(((2 * w) // 3, 0, w, h))
        center_core = orig_img.crop((w // 4, h // 4, (3 * w) // 4, (3 * h) // 4))
        
        # 極速計算 Root Mean Square 統計量
        stat_left = ImageStat.Stat(left_third).rms[0]
        stat_right = ImageStat.Stat(right_third).rms[0]
        stat_center = ImageStat.Stat(center_core).rms[0]
        stat_global = ImageStat.Stat(orig_img).rms[0]
        
        raw_action = "perfect"
        instructions = ""
        
        # ─── 進入毫秒級美學決策鏈 ───
        if stat_left > stat_right * self.imbalance_threshold:
            raw_action = "left"
            instructions = "【請向左平移手機】修正主體偏右情形，使其對齊右側黃金三分線"
        elif stat_right > stat_left * self.imbalance_threshold:
            raw_action = "right"
            instructions = "【請向右平移手機】修正主體偏左情形，使其對齊左側黃金三分線"
        else:
            # 判斷 Z 軸焦距縮放 (Zoom)
            if stat_center < stat_global * 0.88:
                raw_action = "zoom_in"
                instructions = "【請前進或放大焦距】主體在環境中顯得渺小，請靠近以凸顯焦點"
            elif stat_center > stat_global * 1.15:
                raw_action = "zoom_out"
                instructions = "【請後退或縮小焦距】主體逼近邊框壓迫感重，請保留背景美學空間"
            else:
                raw_action = "perfect"
                instructions = "完美黃金比例！畫面結構非常穩定平衡，請直接拍攝"

        # 時序佇列平滑濾波（防跳針）
        self.history_queue.append(raw_action)
        if len(self.history_queue) > self.queue_max_size:
            self.history_queue.pop(0)
        
        final_action = max(set(self.history_queue), key=self.history_queue.count)
        
        if final_action == "perfect" and "完美" not in instructions:
            instructions = "構圖美學判定已達標，畫面呈現高穩定平衡，請按下快門"

        # 幾何裁切優化處理 (輸出 95 高畫質成果)
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
        xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
        
        cropped_img = orig_img.crop((xmin, ymin, xmax, ymax))
        output_buffer = io.BytesIO()
        cropped_img.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        return output_buffer, instructions, final_action
