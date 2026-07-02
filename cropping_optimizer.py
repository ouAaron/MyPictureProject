# cropping_optimizer.py
import cv2
import numpy as np

class AestheticCroppingOptimizer:
    def __init__(self):
        pass

    def optimize_crop_box(self, img, edges, gray, cx, cy):
        h, w = edges.shape
        
        # ─── 1. 仿 AesCrop 精神：引進「天然幾何框架保護網 (Natural Framing)」 ───
        # 利用霍夫圓變換或大弧度檢測，尋找是否有拱門、圓弧等天然框架
        min_crop_w, min_crop_h = int(w // 3.5 * 2), int(h // 3.5 * 2) # 預設最小裁切尺寸
        
        # 快速抓取大弧形線條特徵
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            perimeter = cv2.arcLength(cnt, True)
            if perimeter > 250: # 只關注大面積的幾何結構
                x, y, cw, ch = cv2.boundingRect(cnt)
                # 如果這個結構很大（占比超過全圖 35%），代表是環境中的天然拱門、窗框等
                if (cw * ch) > (w * h * 0.35):
                    # 鎖定邊界，強行保護這個框架不被過度裁切（Over-cropping）
                    min_crop_w = max(min_crop_w, int(cw * 1.05))
                    min_crop_h = max(min_crop_h, int(ch * 1.05))
                    break

        # ─── 2. 仿 AesCrop 精神：升級「動態不對稱偏置」裁切（留白美學） ───
        # 利用 OpenCV 質心矩 (Moments) 計算畫面的視覺重心與不對稱性
        M = cv2.moments(edges)
        if M["m00"] != 0:
            saliency_x = int(M["m10"] / M["m00"])
        else:
            saliency_x = w // 2

        # 動態動態偏置（Offset）計算：讓主角面向的方向或特徵輕的一側保留呼吸空間 (Negative Space)
        offset_x = 0
        # 如果視覺質心明顯偏左，代表主角偏左，我們在右側動態偏置 12% 留白空間
        if saliency_x < w * 0.45:
            offset_x = int(w * 0.12)
        # 如果視覺質心明顯偏右，代表主角偏右，我們在左側動態偏置 12% 留白空間
        elif saliency_x > w * 0.55:
            offset_x = -int(w * 0.12)

        # 將動態美學留白偏置套入中心座標
        optimized_cx = cx + offset_x

        # ─── 3. 幾何邊界安全防護與鎖定 ───
        # 計算邊界，確保最終框的大小有受到天然框架保護，且不會超出圖片邊界
        crop_w = max(int(w // 3.5 * 2), min_crop_w)
        crop_h = max(int(h // 3.5 * 2), min_crop_h)
        
        xmin = int(max(0, optimized_cx - (crop_w // 2)))
        ymin = int(max(0, cy - (crop_h // 2)))
        xmax = int(min(w, xmin + crop_w))
        ymax = int(min(h, ymin + crop_h))
        
        # 再次微調以防止不對稱偏置導致的邊框越界
        if xmax == w: xmin = w - crop_w
        if xmin == 0: xmax = crop_w

        return xmin, ymin, xmax, ymax
