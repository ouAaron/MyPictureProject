# composition_engine.py
from PIL import Image, ImageStat, ImageFilter
import io
import math

class AcademicCompositionEngine:
    def __init__(self):
        # 論文嚴格美學指標門檻值調校
        self.imbalance_threshold = 1.06   # 左右特徵能量失衡門檻 (6%)
        self.ideal_area_min = 0.15        # 論文主體核心核心占比下限 (低於則需 Zoom-in)
        self.ideal_area_max = 0.45        # 論文主體核心核心占比上限 (高於則需 Zoom-out)
        self.border_noise_threshold = 1.25 # 邊緣冗餘雜訊能量門檻

    def analyze(self, image_bytes):
        try:
            orig_img = Image.open(io.BytesIO(image_bytes))
            orig_img = orig_img.convert("RGB")
        except:
            return None, "圖片解析失敗", "hold"
        
        w, h = orig_img.size
        
        # 1. 模擬 U2Net/顯著性檢測：利用高通邊緣濾鏡 (Find Edges) 提取高頻特徵(主體輪廓)
        edge_img = orig_img.filter(ImageFilter.FIND_EDGES).convert("L")
        edge_data = edge_img.load()
        
        # 2. 論文三大敏感區域切片分析 (Shift & Zoom-in 幾何空間)
        left_third = orig_img.crop((0, 0, w // 3, h))
        right_third = orig_img.crop(((2 * w) // 3, 0, w, h))
        
        # 邊緣雜訊區域 (Border Distractions Analysis)
        top_border = edge_img.crop((0, 0, w, int(h * 0.1)))
        bottom_border = edge_img.crop((0, int(h * 0.9), w, h))
        
        # 計算各區間 RMS 能量密度
        stat_left = ImageStat.Stat(left_third).rms[0]
        stat_right = ImageStat.Stat(right_third).rms[0]
        stat_top_edge = ImageStat.Stat(top_border).mean[0]
        stat_bottom_edge = ImageStat.Stat(bottom_border).mean[0]
        
        # 3. 計算主體顯著性邊界占比 (Saliency Box Area Ratio)
        # 尋找高頻特徵點的極值邊界，框出真實主體
        x_coords = []
        y_coords = []
        step = 4 # 步進抽樣加快動態邊緣計算
        for y in range(0, h, step):
            for x in range(0, w, step):
                if edge_data[x, y] > 45: # 顯著性特徵強度門檻
                    x_coords.append(x)
                    y_coords.append(y)
                    
        if len(x_coords) > 10:
            saliency_w = max(x_coords) - min(x_coords)
            saliency_h = max(y_coords) - min(y_coords)
            saliency_area_ratio = (saliency_w * saliency_h) / (w * h)
        else:
            saliency_area_ratio = 0.3 # 預設安全值
            
        instructions = []
        action_type = "hold"
        
        # ─── 論文決策樹推理引擎開始 ───
        
        # 指標 A：水平平移判定 (Shift Task)
        if stat_left > stat_right * self.imbalance_threshold:
            instructions.append("[請向左平移鏡頭] 修正當前主體偏右情形，使視覺特徵靠向黃金分割線位置")
            action_type = "left"
        elif stat_right > stat_left * self.imbalance_threshold:
            instructions.append("[請向右平移鏡頭] 修正當前主體偏左情形，使視覺特徵靠向黃金分割線位置")
            action_type = "right"
            
        # 指標 B：邊緣冗餘與雜訊過濾 (Border Distractions -> 強制觸發 Zoom-in 排除)
        elif stat_bottom_edge > self.border_noise_threshold or stat_top_edge > self.border_noise_threshold:
            instructions.append("[建議放大焦距] 偵測到邊緣存在冗餘干擾物，請微調焦距排除雜訊")
            action_type = "zoom_in"
            
        # 指標 C：主體顯著性占比深度判定 (Zoom-in / Zoom-out Task)
        else:
            if saliency_area_ratio < self.ideal_area_min:
                instructions.append("[建議前進或放大焦距] 視覺主體占比過低，請調整焦距強化視覺中心點")
                action_type = "zoom_in"
            elif saliency_area_ratio > self.ideal_area_max:
                instructions.append("[建議後退或縮小焦距] 視覺主體壓迫感過強，請保留環境美學呼吸空間")
                action_type = "zoom_out"
            else:
                instructions.append("構圖指標已達美學標準，可直接按下拍攝鈕")
                action_type = "perfect"

        # 4. 推薦美學裁剪框幾何優化 (維持高保真度輸出)
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
