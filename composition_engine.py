# composition_engine.py
from PIL import Image, ImageStat, ImageFilter
import io

class AcademicCompositionEngine:
    def __init__(self):
        # 論文美學判定嚴格門檻
        self.imbalance_threshold = 1.05   
        self.ideal_area_min = 0.15        
        self.ideal_area_max = 0.45        
        self.border_noise_threshold = 1.25 

    def analyze(self, image_bytes):
        try:
            orig_img = Image.open(io.BytesIO(image_bytes))
            orig_img = orig_img.convert("RGB")
        except:
            return None, "圖片解析失敗", "hold"
        
        w, h = orig_img.size
        
        # 1. 顯著性高頻邊緣特徵過濾
        edge_img = orig_img.filter(ImageFilter.FIND_EDGES).convert("L")
        edge_data = edge_img.load()
        
        # 2. 空間敏感切片
        left_third = orig_img.crop((0, 0, w // 3, h))
        right_third = orig_img.crop(((2 * w) // 3, 0, w, h))
        
        top_border = edge_img.crop((0, 0, w, int(h * 0.1)))
        bottom_border = edge_img.crop((0, int(h * 0.9), w, h))
        
        stat_left = ImageStat.Stat(left_third).rms[0]
        stat_right = ImageStat.Stat(right_third).rms[0]
        stat_top_edge = ImageStat.Stat(top_border).mean[0]
        stat_bottom_edge = ImageStat.Stat(bottom_border).mean[0]
        
        # 3. 主體顯著性邊界占比計算
        x_coords = []
        y_coords = []
        step = 4
        for y in range(0, h, step):
            for x in range(0, w, step):
                if edge_data[x, y] > 45:
                    x_coords.append(x)
                    y_coords.append(y)
                    
        if len(x_coords) > 10:
            saliency_w = max(x_coords) - min(x_coords)
            saliency_h = max(y_coords) - min(y_coords)
            saliency_area_ratio = (saliency_w * saliency_h) / (w * h)
        else:
            saliency_area_ratio = 0.3
            
        instructions = []
        action_type = "hold"
        
        # 🔥 【核心優化點】：精確轉換為具體、清楚的身體/相機動作指令
        if stat_left > stat_right * self.imbalance_threshold:
            instructions.append("【請將手機向左平移 10 公分】讓視覺主體落入右側三分線交點")
            action_type = "left"
        elif stat_right > stat_left * self.imbalance_threshold:
            instructions.append("【請將手機向右平移 10 公分】讓視覺主體落入左側三分線交點")
            action_type = "right"
        elif stat_bottom_edge > self.border_noise_threshold or stat_top_edge > self.border_noise_threshold:
            instructions.append("【請點選按鈕放大焦距】排除螢幕邊緣多餘的雜草欄杆等雜訊")
            action_type = "zoom_in"
        else:
            if saliency_area_ratio < self.ideal_area_min:
                instructions.append("【請身體往前跨一步，或點選 2.0x / 4.0x 放大焦距】凸顯視覺核心主體")
                action_type = "zoom_in"
            elif saliency_area_ratio > self.ideal_area_max:
                instructions.append("【請身體後退一步，或縮小焦距】保留構圖邊緣的呼吸空間")
                action_type = "zoom_out"
            else:
                instructions.append("完美黃金比例！請維持穩定，直接按下下方按鈕拍攝")
                action_type = "perfect"

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
