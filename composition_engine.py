# composition_engine.py
import cv2
import numpy as np
import io

class AcademicCompositionEngine:
    def __init__(self):
        # 論文美學嚴格參數調校
        self.history_queue = []
        self.queue_max_size = 4 # 提升到 4 幀平滑，讓箭頭和指令穩如磐石、絕對不跳針

    def analyze(self, image_bytes):
        # 1. 讀取二進位圖檔並轉成 OpenCV 格式
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None, "圖片解碼失敗", "hold"
        
        h, w, _ = img.size() if hasattr(img, 'size') else (img.shape[0], img.shape[1], img.shape[2])
        
        # 2. 基礎影像處理：轉灰階、高斯模糊與 Canny 邊緣提取
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 100)
        
        # 3. 仿 CADB 論文：利用 HSV 空間檢測膚色特徵，結合顯著性輪廓判定是否為人像
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # 計算中心 50% 區域的膚色與特徵集中度
        center_y1, center_y2 = h // 4, (3 * h) // 4
        center_x1, center_x2 = w // 4, (3 * w) // 4
        center_edges = edges[center_y1:center_y2, center_x1:center_x2]
        center_skin = skin_mask[center_y1:center_y2, center_x1:center_x2]
        
        # 核心語意分流：若中央區域有明顯膚色且特徵集中，則啟動人像模式
        is_portrait = cv2.countNonZero(center_skin) > (w * h * 0.015) or cv2.countNonZero(center_edges) > cv2.countNonZero(edges) * 0.4
        
        # 4. 仿 CPC 論文：分析最外圍 10% 邊緣的雜訊能量 (Border Distractions)
        border_t = edges[0:int(h*0.1), 0:w]
        border_b = edges[int(h*0.9):h, 0:w]
        border_l = edges[0:h, 0:int(w*0.1)]
        border_r = edges[0:h, int(w*0.9):w]
        
        border_noise_density = (cv2.countNonZero(border_t) + cv2.countNonZero(border_b) + 
                                cv2.countNonZero(border_l) + cv2.countNonZero(border_r)) / (w * h * 0.4)
        
        # 5. 仿 GAIC 論文：切片計算左右三分線的幾何特徵重心位置
        left_zone = edges[0:h, 0:w // 3]
        right_zone = edges[0:h, (2 * w) // 3:w]
        left_weight = cv2.countNonZero(left_zone)
        right_weight = cv2.countNonZero(right_zone)
        
        raw_action = "perfect"
        instructions = ""
        
        # ─── 進入論文標準美學決策鏈 ───
        if is_portrait:
            # 💁 人像模式美學分支：計算重心是否需要 Shift 平移
            if left_weight > right_weight * 1.15:
                raw_action = "left"
                instructions = "【請向左平移手機】修正人物位置，使其完美契合右側黃金三分線"
            elif right_weight > left_weight * 1.15:
                raw_action = "right"
                instructions = "【請向右平移手機】修正人物位置，使其完美契合左側黃金三分線"
            else:
                # 判斷 Z 軸人像面積占比 (Zoom)
                total_saliency_points = cv2.countNonZero(edges[center_y1:center_y2, 0:w])
                area_ratio = total_saliency_points / (cv2.countNonZero(edges) + 1e-5)
                
                if area_ratio < 0.25:
                    raw_action = "zoom_in"
                    instructions = "【請前進或放大焦距】人物在環境中顯得渺小，請靠近以凸顯肖像細節"
                elif area_ratio > 0.65:
                    raw_action = "zoom_out"
                    instructions = "【請後退或縮小焦距】人物逼近邊框壓迫感重，請保留背景美學空間"
                else:
                    raw_action = "perfect"
                    instructions = "完美黃金肖像比例！人物重心與背景完美交融，請直接拍攝"
        else:
            # 🏞️ 景物模式美學分支：先排除邊緣干擾雜訊 (CPC 精神)
            if border_noise_density > 0.12:
                raw_action = "zoom_in"
                instructions = "【請手動放大至 2x / 4x】偵測到邊緣有雜草、欄杆等冗餘干擾物，請微調焦距裁切排除"
            # 景物左右重心平衡度判定
            elif left_weight > right_weight * 1.25:
                raw_action = "left"
                instructions = "【請向左平移鏡頭】大自然視覺重心偏右，請左移平衡光影地景幾何"
            elif right_weight > left_weight * 1.25:
                raw_action = "right"
                instructions = "【請向右平移鏡頭】大自然視覺重心偏左，請右移平衡光影地景幾何"
            else:
                raw_action = "perfect"
                instructions = "風景地平線結構與光影權重極其完美，請直接按下快門"

        # 6. 時序佇列平滑濾波（防跳針）
        self.history_queue.append(raw_action)
        if len(self.history_queue) > self.queue_max_size:
            self.history_queue.pop(0)
        
        final_action = max(set(self.history_queue), key=self.history_queue.count)
        
        # 修正完美狀態的顯示文字
        if final_action == "perfect" and "完美" not in instructions:
            instructions = "構圖美學判定已達標，畫面呈現高穩定平衡，請按下快門"

        # 7. 幾何裁切優化處理 (輸出 95 高畫質成果)
        cx = w // 3 if final_action == "left" else ((2 * w) // 3 if final_action == "right" else w // 2)
        cy = h // 2
        xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
        xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
        
        cropped = img[ymin:ymax, xmin:xmax]
        _, img_encoded = cv2.imencode('.jpg', cropped, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        output_buffer = io.BytesIO(img_encoded.tobytes())
        
        return output_buffer, instructions, final_action
