# subject_classifier.py
import cv2
import numpy as np

class SubjectAdaptiveClassifier:
    def __init__(self):
        # 設定靈敏的三分線失衡門檻（5%）
        self.th_ratio = 1.05

    def detect_and_align(self, img, edges, gray):
        h, w = edges.shape
        
        # 🪐 幾何區域極速像素權重計算 (在 160 規格矩陣上，運算時間低於 1ms)
        left_zone = edges[0:h, 0:w // 3]
        right_zone = edges[0:h, (2 * w) // 3:w]
        center_zone = edges[h // 4 : (3 * h) // 4, w // 4 : (3 * w) // 4]
        
        left_w = cv2.countNonZero(left_zone)
        right_w = cv2.countNonZero(right_zone)
        center_w = cv2.countNonZero(center_zone)
        total_w = cv2.countNonZero(edges) + 1e-5

        # 🪐 對稱性矩陣速算
        half_w = w // 2
        left_half = gray[0:h, 0:half_w]
        right_half = gray[0:h, half_w : half_w * 2]
        right_half_flipped = cv2.flip(right_half, 1)
        
        if left_half.shape == right_half_flipped.shape:
            sym_diff = cv2.absdiff(left_half, right_half_flipped)
            sym_score = 1.0 - (cv2.countNonZero(cv2.threshold(sym_diff, 40, 255, cv2.THRESH_BINARY)[1]) / (half_w * h + 1e-5))
        else:
            sym_score = 0.0

        # 🪐 垂直幾何特徵粗略速算
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        sobel_y_abs = np.uint8(np.absolute(sobel_y))
        vertical_score = cv2.countNonZero(cv2.threshold(sobel_y_abs, 50, 255, cv2.THRESH_BINARY)[1]) / total_w

        raw_action = "perfect"
        instructions = ""
        mode_key = "RoT"

        # ─── 進入全即時動態純指令引導流 ───
        if sym_score > 0.80:
            mode_key = "Symmetric"
            if left_w > right_w * self.th_ratio:
                raw_action = "left"
                instructions = "請向左平移鏡頭，微調兩側幾何使其對齊中軸"
            elif right_w > left_w * self.th_ratio:
                raw_action = "right"
                instructions = "請向右平移鏡頭，微調兩側幾何使其對齊中軸"
            else:
                raw_action = "perfect"
                instructions = "左右對稱平衡，請保持相機穩定直接拍攝"

        elif vertical_score > 0.40:
            mode_key = "Vertical"
            if left_w > right_w * 1.08:
                raw_action = "left"
                instructions = "請向左平移手機，校正垂直線條使其保持垂直對齊"
            elif right_w > left_w * 1.08:
                raw_action = "right"
                instructions = "請向右平移手機，校正垂直線條使其保持垂直對齊"
            else:
                raw_action = "perfect"
                instructions = "垂直幾何已對齊，請維持相機穩定直接拍攝"

        elif center_w > total_w * 0.45:
            mode_key = "Center"
            if left_w > right_w * 1.08:
                raw_action = "left"
                instructions = "請向左輕移鏡頭，將核心主角拉回畫面正中央"
            elif right_w > left_w * 1.08:
                raw_action = "right"
                instructions = "請向右輕移鏡頭，將核心主角拉回畫面正中央"
            else:
                raw_action = "perfect"
                instructions = "主角已精確居中，請維持相機穩定準備拍攝"

        elif total_w > (w * h * 0.40):
            mode_key = "Fill"
            raw_action = "zoom_out"
            instructions = "主體占比過大產生壓迫感，請退後保留呼吸空間"

        else:
            mode_key = "RoT"
            if left_w > right_w * self.th_ratio:
                raw_action = "left"
                instructions = "請向左平移手機，使主體對齊右側黃金網格線"
            elif right_w > left_w * self.th_ratio:
                raw_action = "right"
                instructions = "請向右平移手機，使主體對齊左側黃金網格線"
            else:
                if center_w < total_w * 0.22:
                    raw_action = "zoom_in"
                    instructions = "請放大焦距或向前走近，以凸顯核心焦點細節"
                elif center_w > total_w * 0.40:
                    raw_action = "zoom_out"
                    instructions = "環境呼吸空間偏少，請稍微退後或縮小畫面倍率"
                else:
                    raw_action = "perfect"
                    instructions = "畫面結構穩定平衡，請直接按下快門"

        return f"{mode_key}@{instructions}", raw_action
