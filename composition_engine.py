# composition_engine.py
import cv2
import numpy as np
import io

class AcademicCompositionEngine:
    def __init__(self):
        self.history_queue = []
        self.queue_max_size = 3 # 3幀平滑防跳針

    def analyze(self, image_bytes):
        # 1. 解碼圖檔並取得長寬
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, "圖片解析失敗", "hold"
        
        h, w, _ = img.shape
        
        # 2. 轉灰階與快速邊緣提取
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        
        # 3. 膚色檢測（HSV 空間速算）
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        center_skin = skin_mask[h // 4 : (3 * h) // 4, w // 4 : (3 * w) // 4]
        
        # 4. 霍夫直線檢測（算大樓的垂直線）
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=40, minLineLength=30, maxLineGap=10)
        vertical_line_count = 0
        total_lines = 0
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                total_lines += 1
                # 計算線條角度
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                # 接近 90 度（75~105度）定義為垂直大樓幾何線
                if 75 <= angle <= 105:
                    vertical_line_count += 1
        
        # ─── 語意類型分流決策 ───
        # 條件 A：膚色像素夠多 ➔ 人像模式
        if cv2.countNonZero(center_skin) > (w * h * 0.015):
            mode_tag = "portrait"
        # 條件 B：垂直直線占比高，或是畫面充滿高密度幾何 ➔ 大樓建築模式
        elif total_lines > 5 and (vertical_line_count / total_lines) > 0.35:
            mode_tag = "building"
        else:
            mode_tag = "scenery" # 一般風景
            
        # 5. 三分線幾何區域權重速算
        left_zone = edges[0:h, 0:w // 3]
        right_zone = edges[0:h, (2 * w) // 3:w]
        left_weight = cv2.countNonZero(left_zone)
        right_weight = cv2.countNonZero(right_zone)
        
        raw_action = "perfect"
        instructions = ""
        
        # ─── 根據探測到的物體，套用不同論文標準 ───
        if mode_tag == "portrait":
            # 💁 人像模式：對齊黃金三分線與人像占比
            if left_weight > right_weight * 1.08:
                raw_action = "left"
                instructions = "【請向左平移手機】修正人物位置，使其對齊右側黃金三分線"
            elif right_weight > left_weight * 1.08:
                raw_action = "right"
                instructions = "【請向右平移手機】修正人物位置，使其對齊左側黃金三分線"
            else:
                center_edges = edges[h // 4 : (3 * h) // 4, w // 4 : (3 * w) // 4]
                area_ratio = cv2.countNonZero(center_edges) / (cv2.countNonZero(edges) + 1e-5)
                if area_ratio < 0.22:
                    raw_action = "zoom_in"
                    instructions = "【請身體往前跨一步】人物在畫面中過於渺小，請拉近凸顯焦點"
                elif area_ratio > 0.60:
                    raw_action = "zoom_out"
                    instructions = "【請身體後退一步】人像占比過大產生壓迫感，請退後保留呼吸空間"
                else:
                    raw_action = "perfect"
                    instructions = "完美黃金肖像構圖！請維持穩定直接拍攝"
                    
        elif mode_tag == "building":
            # 🏢 大樓建築模式：嚴格注重「物理垂直線對齊與手機傾角調整」
            # 如果左右失衡，代表大樓拍歪了或透視點偏了，引導移動步伐
            if left_weight > right_weight * 1.12:
                raw_action = "left"
                instructions = "【請身體向左跨兩步】修正大樓幾何透視，讓建築物中軸線回歸正中"
            elif right_weight > left_weight * 1.12:
                raw_action = "right"
                instructions = "【請身體向右跨兩步】修正大樓幾何透視，讓建築物中軸線回歸正中"
            else:
                # 檢查頂部與底部的邊緣雜訊占比
                top_edges = cv2.countNonZero(edges[0:int(h*0.12), 0:w])
                if top_edges > cv2.countNonZero(edges) * 0.15:
                    raw_action = "zoom_out"
                    instructions = "【請手機稍微向下微傾】避免大樓頂部被截斷，保留建築幾何的完整度"
                else:
                    raw_action = "perfect"
                    instructions = "大樓垂直軸線已完美對齊！透視結構具備宏偉縱深，請拍攝"
                    
        else:
            # 🏞️ 一般景物風景模式：追求地平線的平衡
            if left_weight > right_weight * 1.20:
                raw_action = "left"
                instructions = "【請水平向左微移】修正大自然視覺重心，平衡環境光影結構"
            elif right_weight > left_weight * 1.20:
                raw_action = "right"
                instructions = "【請水平向右微移】修正大自然視覺重心，平衡環境光影結構"
            else:
                raw_action = "perfect"
                instructions = "大自然景物水平比例非常平衡，請按下快門"

        # 6. 時序平滑濾波（防跳針）
        self.history_queue.append(raw_action)
        if len(self.history_queue) > self.queue_max_size:
            self.history_queue.pop(0)
        
        final_action = max(set(self.history_queue), key=self.history_queue.count)
        
        if final_action == "perfect" and "完美" not in instructions:
            instructions = "美學結構已趨於穩定，畫面幾何平衡合格，請按下快門"

        # 7. 智慧優化裁切與輸出
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
        xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
        
        cropped = img[ymin:ymax, xmin:xmax]
        _, img_encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        return io.BytesIO(img_encoded.tobytes()), instructions, final_action
