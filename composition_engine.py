# composition_engine.py
from PIL import Image, ImageStat, ImageFilter
import io

class AcademicCompositionEngine:
    def __init__(self):
        self.imbalance_threshold = 1.08   # 調緊失衡門檻至 8%，降低敏感度避免頻繁震盪
        self.ideal_area_min = 0.15        
        self.ideal_area_max = 0.45        
        
        # 🔥 【技術突破點 1】：時序平滑狀態快取（防跳針機制）
        self.history_queue = []
        self.queue_max_size = 3 # 連續 3 幀確認才切換指令

    def analyze(self, image_bytes):
        try:
            orig_img = Image.open(io.BytesIO(image_bytes))
            orig_img = orig_img.convert("RGB")
        except:
            return None, "圖片解析失敗", "hold"
        
        w, h = orig_img.size
        
        # 提取高頻邊緣特徵
        edge_img = orig_img.filter(ImageFilter.FIND_EDGES).convert("L")
        edge_data = edge_img.load()
        
        # 空間敏感區切割
        left_third = orig_img.crop((0, 0, w // 3, h))
        right_third = orig_img.crop(((2 * w) // 3, 0, w, h))
        center_core = orig_img.crop((w // 4, h // 4, (3 * w) // 4, (3 * h) // 4))
        
        stat_left = ImageStat.Stat(left_third).rms[0]
        stat_right = ImageStat.Stat(right_third).rms[0]
        stat_center = ImageStat.Stat(center_core).rms[0]
        stat_global = ImageStat.Stat(orig_img).rms[0]
        
        # 提取邊緣干擾
        top_border = edge_img.crop((0, 0, w, int(h * 0.1)))
        bottom_border = edge_img.crop((0, int(h * 0.9), w, h))
        stat_top_edge = ImageStat.Stat(top_border).mean[0]
        stat_bottom_edge = ImageStat.Stat(bottom_border).mean[0]

        # 🔥 【技術突破點 2】：區分人物與景物 (Semantic Differentiation)
        # 統計中心區域與全圖的高頻特徵密度比值
        edge_center = ImageStat.Stat(center_core.filter(ImageFilter.FIND_EDGES).convert("L")).mean[0]
        edge_global = ImageStat.Stat(edge_img).mean[0]
        
        # 如果中心邊緣特徵極度集中（比全球高出很多），代表是具有複雜輪廓的人像/主體
        # 如果特徵分散，且水平/垂直能量對比明顯，代表是風景/環境
        is_portrait = edge_center > edge_global * 1.3
        
        raw_action = "perfect"
        instructions = ""
        
        # 根據語意切換不同美學標準
        if is_portrait:
            # 人像模式：嚴格遵循三分法交點引導主體
            if stat_left > stat_right * self.imbalance_threshold:
                raw_action = "left"
                instructions = "【請向左平移 10 公分】微調人像位置，使其對齊右側黃金分割線"
            elif stat_right > stat_left * self.imbalance_threshold:
                raw_action = "right"
                instructions = "【請向右平移 10 公分】微調人像位置，使其對齊左側黃金分割線"
            else:
                if stat_center < stat_global * 0.85:
                    raw_action = "zoom_in"
                    instructions = "【請前進或放大焦距】當前人物在畫面中過於渺小，請放大以凸顯主體"
                elif stat_center > stat_global * 1.25:
                    raw_action = "zoom_out"
                    instructions = "【請後退或縮小焦距】人物占比過大產生壓迫感，請退後保留背景空間"
                else:
                    raw_action = "perfect"
                    instructions = "人物比例絕佳！符合黃金分割美學，請直接拍攝"
        else:
            # 景物模式：著重於邊緣冗餘干擾過濾與地平線平衡
            if stat_bottom_edge > 1.3 or stat_top_edge > 1.3:
                raw_action = "zoom_in"
                instructions = "【請稍微放大焦距】偵測到風景邊緣存在雜亂干擾物，請微調焦距排除雜訊"
            elif stat_left > stat_right * 1.12: # 風景模式左右容忍度放寬，避免風景細節導致頻繁提示
                raw_action = "left"
                instructions = "【請水平向左微移鏡頭】修正大自然景物視覺重心，平衡水平視覺特徵"
            elif stat_right > stat_left * 1.12:
                raw_action = "right"
                instructions = "【請水平向右微移鏡頭】修正大自然景物視覺重心，平衡水平視覺特徵"
            else:
                raw_action = "perfect"
                instructions = "風景地平線與環境光影結構非常完美，可直接拍攝"

        # 🔥 【防跳針演算法】：時序佇列平滑濾波
        self.history_queue.append(raw_action)
        if len(self.history_queue) > self.queue_max_size:
            self.history_queue.pop(0)
            
        # 進行多數決投票（Majority Voting）
        final_action = max(set(self.history_queue), key=self.history_queue.count)
        
        # 若最終投票結果變更，同步更新對應的文字
        if final_action == "perfect" and "完美" not in instructions:
            instructions = "構圖指標已趨於穩定，美學標準合格，請直接拍攝"

        # 美學幾何優化裁剪
        cx, cy = (w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)), h // 2
        xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
        xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
        
        cropped_img = orig_img.crop((xmin, ymin, xmax, ymax))
        output_buffer = io.BytesIO()
        cropped_img.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        return output_buffer, instructions, final_action
