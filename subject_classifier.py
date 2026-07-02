# subject_classifier.py
import cv2
import numpy as np

class SubjectAdaptiveClassifier:
    def __init__(self):
        # 11大美學類別信心門檻值與失衡比例
        self.th_ratio = 1.08

    def detect_and_align(self, img, edges, gray):
        h, w = edges.shape
        
        # ─── 核心演算法：11 大幾何與語意特徵矩陣計算 ───
        
        # 1. 三分法 (RoT) & 中心構圖 (Center) 重心統計
        left_zone = edges[0:h, 0:w // 3]
        right_zone = edges[0:h, (2 * w) // 3:w]
        center_zone = edges[h // 4 : (3 * h) // 4, w // 4 : (3 * w) // 4]
        
        left_w = cv2.countNonZero(left_zone)
        right_w = cv2.countNonZero(right_zone)
        center_w = cv2.countNonZero(center_zone)
        total_w = cv2.countNonZero(edges) + 1e-5

        # 2. 霍夫直線變換 ── 用於偵測水平、垂直、對角線與引導線
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=40, maxLineGap=15)
        hori_lines = 0
        vert_lines = 0
        diag_lines = 0
        v_points = [] # 消失點交點分析
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                
                if angle <= 15 or angle >= 165: # 水平線 (0度附近)
                    hori_lines += 1
                elif 75 <= angle <= 105: # 垂直線 (90度附近)
                    vert_lines += 1
                elif 25 <= angle <= 65 or 115 <= angle <= 155: # 對角線 (45度附近)
                    diag_lines += 1
                    v_points.append((x1, y1, x2, y2))

        # 3. 對稱構圖 (Symmetry) 矩陣相減
        half_w = w // 2
        left_half = gray[0:h, 0:half_w]
        right_half = gray[0:h, half_w : half_w * 2]
        right_half_flipped = cv2.flip(right_half, 1)
        # 防止因手機畫面裁切長寬不對等導致的微小維度不合
        if left_half.shape == right_half_flipped.shape:
            sym_diff = cv2.absdiff(left_half, right_half_flipped)
            sym_score = 1.0 - (cv2.countNonZero(cv2.threshold(sym_diff, 35, 255, cv2.THRESH_BINARY)[1]) / (half_w * h))
        else:
            sym_score = 0.0

        # 4. 重複圖騰 (Pattern) & 滿版構圖 (Fill the Frame) 特徵密度分析
        # 切割成九宮格，若每個網格的邊緣特徵極度均勻且密集，則為圖騰
        grid_counts = []
        for i in range(3):
            for j in range(3):
                grid = edges[i*(h//3):(i+1)*(h//3), j*(w//3):(j+1)*(w//3)]
                grid_counts.append(cv2.countNonZero(grid))
        grid_std = np.std(grid_counts)
        grid_mean = np.mean(grid_counts) + 1e-5

        # 5. 膚色偵測（用於人像輔助判定）
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        skin_mask = cv2.inRange(hsv, np.array([0, 20, 70]), np.array([20, 255, 255]))
        has_skin = cv2.countNonZero(skin_mask[h//4:(3*h)//4, w//4:(3*w)//4]) > (w * h * 0.015)

        # ─── 11 大黃金構圖類別語意決策樹分配 ───
        raw_action = "perfect"
        instructions = ""

        # 1. 對稱構圖 (Symmetry) 
        if sym_score > 0.82:
            mode_tag = "Symmetry"
            if left_w > right_w * 1.08:
                raw_action = "left"
                instructions = "【請向左平移鏡頭】校正兩側幾何，使鏡像對稱軸線回歸畫面中軸 "
            elif right_w > left_w * 1.08:
                raw_action = "right"
                instructions = "【請向右平移鏡頭】校正兩側幾何，使鏡像對稱軸線回歸畫面中軸 "
            else:
                instructions = "對稱美學完美達成！左右雙側倒影結構極其平衡，請按下快門 "

        # 2. 重複圖騰 (Pattern) 
        elif grid_mean > 300 and (grid_std / grid_mean) < 0.28:
            mode_tag = "Pattern"
            instructions = "【重複圖騰模式】當前環境富有規律紋理之美，建議維持現狀直接拍攝 "

        # 3. 滿版構圖 (Fill the Frame) 
        elif total_w > (w * h * 0.45):
            mode_tag = "Fill"
            raw_action = "zoom_out"
            instructions = "【請身體後退一步】主體已滿版壓迫，退後可保留邊緣美學呼吸空間 "

        # 4. 引導線構圖 (Leading Lines) 
        elif len(v_points) >= 4 and vert_lines >= 2:
            mode_tag = "Leading Lines"
            if left_w > right_w * 1.10:
                raw_action = "left"
                instructions = "【請身體向左跨一步】讓空間引導線完美匯聚於畫面視覺中心點 "
            elif right_w > left_w * 1.10:
                raw_action = "right"
                instructions = "【請身體向右跨一步】讓空間引導線完美匯聚於畫面視覺中心點 "
            else:
                instructions = "縱深引導線完美聚焦！幾何線條已匯聚至消失點，請拍攝 "

        # 5. 三角形構圖 (Triangle) 
        elif hori_lines >= 1 and diag_lines >= 2 and center_w > total_w * 0.35:
            mode_tag = "Triangle"
            instructions = "【三角形構圖】多維度線條已組成穩固的三角美學，請直接按下快門 "

        # 6. 垂直構圖 (Vertical) 
        elif vert_lines > hori_lines * 2 and vert_lines >= 3:
            mode_tag = "Vertical"
            if left_w > right_w * 1.12:
                raw_action = "left"
                instructions = "【請向左平移手機】修正高聳垂直幾何，保持大樓軸線挺拔不傾斜 "
            elif right_w > left_w * 1.12:
                raw_action = "right"
                instructions = "【請向右平移手機】修正高聳垂直幾何，保持大樓軸線挺拔不傾斜 "
            else:
                instructions = "垂直線條頂天立地！建築宏偉比例已精確校正，請拍攝 "

        # 7. 水平構圖 (Horizontal) 
        elif hori_lines > vert_lines * 2 and hori_lines >= 2:
            mode_tag = "Horizontal"
            instructions = "【水平面完美平衡】地平線平穩對齊，環境光影權重優良，可直接拍攝 "

        # 8. 對角線構圖 (Diagonal) 
        elif diag_lines >= 3:
            mode_tag = "Diagonal"
            instructions = "【對角線構圖】視覺主體沿斜向維度延伸，富有動態節奏感，請拍攝 "

        # 9. 曲線構圖 (Curved) 
        elif len(v_points) >= 2 and hori_lines >= 1 and grid_std > 200:
            mode_tag = "Curved"
            instructions = "【曲線美學模式】畫面具備優美蜿蜒流向，請保持穩定直接拍攝 "

        # 10. 中心構圖 (Center) 
        elif center_w > total_w * 0.55 or (center_w > total_w * 0.40 and has_skin):
            mode_tag = "Center"
            if left_w > right_w * 1.15:
                raw_action = "left"
                instructions = "【請向左平移】將視覺核心主角修正拉回屏幕正中央位置 "
            elif right_w > left_w * 1.15:
                raw_action = "right"
                instructions = "【請向右平移】將視覺核心主角修正拉回屏幕正中央位置 "
            else:
                instructions = "主角已精確鎖定中心！視覺焦點極度集中，請按下快門 "

        # 11. 三分法構圖 (Rule of Thirds) 
        else:
            mode_tag = "RoT"
            if left_w > right_w * self.th_ratio:
                raw_action = "left"
                instructions = "【請向左平移手機】修正主體偏右情形，使其對齊右側三分線交點 "
            elif right_w > left_w * self.th_ratio:
                raw_action = "right"
                instructions = "【請向右平移手機】修正主體偏左情形，使其對齊左側三分線交點 "
            else:
                if center_w < total_w * 0.20:
                    raw_action = "zoom_in"
                    instructions = "【請放大焦距或走近】主體在三分網格中過於渺小，請放大以凸顯焦點 "
                else:
                    instructions = "符合經典三分法美學！畫面結構非常穩定平衡，請直接拍攝 "

        # 將偵測到的模式名稱與指令綁定，方便前端提取亮燈
        return f"{mode_tag}|{instructions}", raw_action

        return instructions, raw_action
