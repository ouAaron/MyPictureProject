# composition_engine.py
from PIL import Image, ImageStat
import io

class AcademicCompositionEngine:
    def __init__(self):
        # 論文美學嚴格門檻值調校
        self.imbalance_threshold = 1.05  # 左右能量比例超過 5% 即判定失衡
        self.zoom_in_threshold = 0.88     # 中央核心特徵密度低於 88% 判定過遠
        self.zoom_out_threshold = 1.12    # 中央核心特徵密度高於 112% 判定壓迫

    def analyze(self, image_bytes):
        try:
            orig_img = Image.open(io.BytesIO(image_bytes))
            orig_img = orig_img.convert("RGB")
        except:
            return None, null
        
        w, h = orig_img.size
        
        # 論文空間幾何分割
        left_third = orig_img.crop((0, 0, w // 3, h))
        right_third = orig_img.crop(((2 * w) // 3, 0, w, h))
        center_core = orig_img.crop((w // 4, h // 4, (3 * w) // 4, (3 * h) // 4))
        
        # 計算各美學敏感區之均方根能量 (Root Mean Square)
        stat_left = ImageStat.Stat(left_third).rms[0]
        stat_right = ImageStat.Stat(right_third).rms[0]
        stat_center = ImageStat.Stat(center_core).rms[0]
        stat_global = ImageStat.Stat(orig_img).rms[0]
        
        instructions = []
        action_type = "hold"  # 用於前端即時控制倍率的燈號訊號 (left, right, zoom_in, zoom_out, perfect)
        
        # 1. 水平維度（左右平移）判定
        if stat_left > stat_right * self.imbalance_threshold:
            instructions.append("[請向左平移鏡頭] 修正當前主體偏右情形，使視覺特徵靠向黃金分割線位置")
            action_type = "left"
        elif stat_right > stat_left * self.imbalance_threshold:
            instructions.append("[請向右平移鏡頭] 修正當前主體偏左情形，使視覺特徵靠向黃金分割線位置")
            action_type = "right"
        else:
            # 2. 深度維度（Z軸縮放）判定
            if stat_center < stat_global * self.zoom_in_threshold:
                instructions.append("[建議前進或放大焦距] 核心特徵占比過低，建議縮減環境冗餘邊緣")
                action_type = "zoom_in"
            elif stat_center > stat_global * self.zoom_out_threshold:
                instructions.append("[建議後退或縮小焦距] 視覺主體壓迫感過強，建議保留畫面呼吸空間")
                action_type = "zoom_out"
            else:
                instructions.append("構圖指標已達美學標準，可直接按下拍攝鈕")
                action_type = "perfect"

        # 計算推薦裁剪框（美學構圖優化）
        if action_type == "left":
            cx, cy = w // 3, h // 2
        elif action_type == "right":
            cx, cy = (2 * w) // 3, h // 2
        else:
            cx, cy = w // 2, h // 2

        xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
        xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
        
        cropped_img = orig_img.crop((xmin, ymin, xmax, ymax))
        
        output_buffer = io.BytesIO()
        cropped_img.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        return output_buffer, " | ".join(instructions), action_type
