# face_tracker.py
import cv2
import numpy as np

class iPhoneFaceTracker:
    def __init__(self):
        # 載入 OpenCV 內建輕量化的臉部特徵級聯分類器（毫秒級速算，絕不卡頓）
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def locate_face(self, gray_img):
        # 進行極速臉部偵測
        faces = self.face_cascade.detectMultiScale(gray_img, scaleFactor=1.2, minNeighbors=3, minSize=(30, 30))
        
        if len(faces) > 0:
            # 取得偵測到的第一個臉部座標 (x, y, width, height)
            fx, fy, fw, fh = faces[0]
            h, w = gray_img.shape
            
            # 將座標轉換為 0.0 ~ 1.0 的相對比例，方便前端 Canvas 進行硬體加速渲染
            relative_x = float((fx + fw / 2) / w)
            relative_y = float((fy + fh / 2) / h)
            relative_size = float(fw) # 臉部寬度，用於調整框框大小
            
            return True, relative_x, relative_y, relative_size
        
        return False, 0.0, 0.0, 0.0
