# subject_classifier.py
import cv2
import numpy as np

class SubjectAdaptiveClassifier:
    def __init__(self):
        # 微調容忍度參數（調緊至 6%，讓平移與縮放判定更細緻穩定）
        self.th_ratio = 1.06

    def detect_and_align(self, img, edges, gray):
        h, w = edges.shape
        
        # ─── 核心幾何特徵矩陣計算 ───
        left_zone = edges[0:h, 0:w // 3]
        right_zone = edges[0:h, (2 * w) // 3:w]
        center_zone = edges[h // 4 : (3 * h) // 4, w // 4 : (3 * w) // 4]
        
        left_w = cv2.countNonZero(left_zone)
        right_w = cv2.countNonZero(right_zone)
        center_w = cv2.countNonZero(center_zone)
        total_w = cv2.countNonZero(edges) + 1e-5

        # 霍夫直線變換 ── 用於精確提取環境幾何線條
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=45, minLineLength=40, maxLineGap=15)
        hori_lines = 0
        vert_lines = 0
        diag_lines = 0
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                if angle <= 15 or angle >= 165:
                    hori_lines += 1
                elif 75 <= angle <= 105:
                    vert_lines += 1
                elif 25 <= angle <= 65 or 115 <= angle <= 155:
                    diag_lines += 1

        # 影像對稱性矩陣計算
        half_w = w // 2
        left_half = gray[0:h, 0:half_w]
        right_half = gray[0:h, half_w : half_w * 2]
        right_half_flipped = cv2.flip(right_half, 1)
        if left_half.shape == right_half_flipped.shape:
            sym_diff = cv2.absdiff(left_half, right_half_flipped)
            sym_score = 1.0 - (cv2.countNonZero(cv2.threshold(sym_diff, 35, 255, cv2.THRESH_BINARY)[1]) / (half_w * h))
        else:
            sym_score = 0.0

        # 九宮格特徵密度分析
        grid_counts = []
        for i in range(3):
            for j in range(3):
                grid = edges[i*(h//3):(i+1)*(h//3), j*(w//3):(j+1)*(w//3)]
                grid_counts.append(cv2.countNonZero(grid))
        grid_std = np.std(grid_counts)
        grid_mean = np.mean(grid_counts) + 1e-5

        # 決策動作與純物理指導語句 (徹底移除所有構圖專有名詞)
        raw_action = "perfect"
        instructions = ""

        # 1. 強對稱場景引導
        if sym_score > 0.82:
            if left_w > right_w * 1.06:
                raw_action = "left"
                instructions = "請向左平移鏡頭，微調兩側幾何使其對齊中軸"
            elif right_w > left_w * 1.06:
                raw_action = "right"
                instructions = "請向右平移鏡頭，微調兩側幾何使其對齊中軸"
            else:
                instructions = "位置已完美平衡，請保持穩定直接拍攝"

        # 2. 密集重複紋理場景
        elif grid_mean > 300 and (grid_std / grid_mean) < 0.28:
            instructions = "環境結構分布均勻，請維持現狀直接拍攝"

        # 3. 主體過於逼近邊框
        elif total_w > (w * h * 0.45):
            raw_action = "zoom_out"
            instructions = "【請身體後退一步】主體占比過大，退後可保留邊緣美學空間"

        # 4. 具備明顯空間縱深線條的場景
        elif total_lines > 5 and vert_lines >= 2 and diag_lines >= 2:
            if left_w > right_w * 1.08:
                raw_action = "left"
                instructions = "請身體向左跨一步，讓空間延伸線條匯聚於正中央"
            elif right_w > left_w * 1.08:
                raw_action = "right"
                instructions = "請身體向右跨一步，讓空間延伸線條匯聚於正中央"
            else:
                instructions = "線條縱深已精確對齊，請維持穩定直接拍攝"

        # 5. 高聳垂直幾何場景（如大樓、柱子）
        elif vert_lines > hori_lines * 2 and vert_lines >= 3:
            if left_w > right_w * 1.08:
                raw_action = "left"
                instructions = "請向左平移手機，校正垂直線條使其保持挺拔"
            elif right_w > left_w * 1.08:
                raw_action = "right"
                instructions = "請向右平移手機，校正垂直線條使其保持挺拔"
            else:
                instructions = "垂直結構已精確校正，請直接按下快門"

        # 6. 強烈中心集中場景
        elif center_w > total_w * 0.45:
            if left_w > right_w * 1.10:
                raw_action = "left"
                instructions = "請向左平移，將核心主角修正拉回畫面正中央"
            elif right_w > left_w * 1.10:
                raw_action = "right"
                instructions = "請向右平移，將核心主角修正拉回畫面正中央"
            else:
                instructions = "主角已精確鎖定中心，請直接按下快門"

        # 7. 標準三分法場景微調 (最純粹的 PhotoFramer 原生機制)
        else:
            if left_w > right_w * self.th_ratio:
                raw_action = "left"
                instructions = "請向左平移手機，使主體對齊右側黃金網格線"
            elif right_w > left_w * self.th_ratio:
                raw_action = "right"
                instructions = "請向右平移手機，使主體對齊左側黃金網格線"
            else:
                if center_w < total_w * 0.20:
                    raw_action = "zoom_in"
                    instructions = "請放大焦距或向前走近，以凸顯核心焦點細節"
                else:
                    instructions = "畫面結構非常穩定平衡，請直接按下快門"

        # 為了跟前端配合，我們保留一個簡單的預設 tag，但在提示框內不會顯示
        return f"LIVE|{instructions}", raw_action
