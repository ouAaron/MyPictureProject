# subject_classifier.py
from PIL import Image, ImageStat

class SubjectAdaptiveClassifier:
    def __init__(self):
        # 設定靈敏的三分線失衡門檻（5%）
        self.th_ratio = 1.05

    def detect_and_align_fast(self, orig_img):
        w, h = orig_img.size
        
        # 🪐 空間幾何三分區域切片（幾何速算，一進去就能提供建議）
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
        mode_key = "RoT"

        # ─── 進入毫秒級純動作指令引導流 ───
        if stat_left > stat_right * self.th_ratio:
            raw_action = "left"
            instructions = "請向左平移手機，使主體對齊右側黃金網格線"
        elif stat_right > stat_left * self.th_ratio:
            raw_action = "right"
            instructions = "請向右平移手機，使主體對齊左側黃金網格線"
        else:
            # 左右平衡時，即時運算 Z 軸的焦距指引
            if stat_center < stat_global * 0.88:
                raw_action = "zoom_in"
                instructions = "請放大焦距或向前走近，以凸顯核心焦點細節"
            elif stat_center > stat_global * 1.15:
                raw_action = "zoom_out"
                instructions = "環境呼吸空間偏少，請稍微退後或縮小畫面倍率"
            else:
                raw_action = "perfect"
                instructions = "畫面結構穩定平衡，請直接按下快門"

        return f"{mode_key}@{instructions}", raw_action
