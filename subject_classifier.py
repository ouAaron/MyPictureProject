# subject_classifier.py
import cv2
import numpy as np

class SubjectAdaptiveClassifier:
    def __init__(self):
        # 論文比例容忍門檻
        self.portrait_imbalance = 1.08
        self.building_imbalance = 1.12

    def detect_and_align(self, img, edges, gray):
        h, w, _ = img.shape
        
        # 1. 膚色特徵提取（HSV 空間速算）
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        center_skin = skin_mask[h // 4 : (3 * h) // 4, w // 4 : (3 * w) // 4]
        
        # 2. 霍夫直線檢測（仿 COMPASS 論文：提取大樓垂直幾何線條）
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=30, maxLineGap=10)
        vertical_lines = 0
        total_lines = 0
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                total_lines += 1
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                # 75~105 度定義為垂直大樓結構線
                if 75 <= angle <= 105:
                    vertical_lines += 1

        # 3. 核心語意類型判定
        if cv2.countNonZero(center_skin) > (w * h * 0.015):
            mode_tag = "portrait"
        elif total_lines > 5 and (vertical_lines / total_lines) > 0.35:
            mode_tag = "building"
        else:
            mode_tag = "scenery"

        # 4. 三分線左右幾何能量計算
        left_zone = edges[0:h, 0:w // 3]
        right_zone = edges[0:h, (2 * w) // 3:w]
        left_weight = cv2.countNonZero(left_zone)
        right_weight = cv2.countNonZero(right_zone)

        # 5. 依據物體種類，動態輸出專屬的拍攝角度與距離指引
        raw_action = "perfect"
        instructions = ""

        if mode_tag == "portrait":
            # 💁 人像模式標準：調整水平平移與安全距離
            if left_weight > right_weight * self.portrait_imbalance:
                raw_action = "left"
                instructions = "【請向左平移手機】修正人物位置，使其對齊右側黃金三分線"
            elif right_weight > left_weight * self.portrait_imbalance:
                raw_action = "right"
                instructions = "【請向右平移手機】修正人物位置，使其對齊左側黃金三分線"
            else:
                center_edges = edges[h // 4 : (3 * h) // 4, w // 4 : (3 * w) // 4]
                area_ratio = cv2.countNonZero(center_edges) / (cv2.countNonZero(edges) + 1e-5)
                if area_ratio < 0.22:
                    raw_action = "zoom_in"
                    instructions = "【請身體往前跨一步】人物在環境中顯得渺小，請靠近以凸顯焦點"
                elif area_ratio > 0.60:
                    raw_action = "zoom_out"
                    instructions = "【請身體後退一步】人像占比過大產生壓迫感，請退後保留呼吸空間"
                else:
                    raw_action = "perfect"
                    instructions = "完美黃金肖像構圖！人物重心與背景完美交融，請直接拍攝"

        elif mode_tag == "building":
            # 🏢 大樓建築模式標準：調整物理透視視角與手機俯仰角（View-change 精神）
            if left_weight > right_weight * self.building_imbalance:
                raw_action = "left"
                instructions = "【請身體向左跨兩步】修正大樓幾何透視，讓建築物中軸線回歸正中"
            elif right_weight > left_weight * self.building_imbalance:
                raw_action = "right"
                instructions = "【請身體向右跨兩步】修正大樓幾何透視，讓建築物中軸線回歸正中"
            else:
                top_edges = cv2.countNonZero(edges[0:int(h*0.12), 0:w])
                if top_edges > cv2.countNonZero(edges) * 0.15:
                    raw_action = "zoom_out"
                    instructions = "【請將手機稍微向下微傾】避免大樓頂部被截斷，保留建築幾何的完整度"
                else:
                    raw_action = "perfect"
                    instructions = "大樓垂直軸線已完美對齊！透視結構具備宏偉縱深，請拍攝"

        else:
            # 🏞️ 一般景物模式標準：地平線平衡
            if left_weight > right_weight * 1.20:
                raw_action = "left"
                instructions = "【請水平向左微移】修正大自然視覺重心，平衡環境光影結構"
            elif right_weight > left_weight * 1.20:
                raw_action = "right"
                instructions = "【請水平向右微移】修正大自然視覺重心，平衡環境光影結構"
            else:
                raw_action = "perfect"
                instructions = "大自然景物水平比例非常平衡，請按下快門"

        return instructions, raw_action
