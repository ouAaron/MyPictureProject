# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
import cv2
import numpy as np
import io
from PIL import Image

app = FastAPI(title="PhotoFramer Lightweight API")

@app.post("/analyze-composition")
async def analyze_composition(file: UploadFile = File(...)):
    # 1. 讀取手機傳過來的照片檔案
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    orig_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if orig_img is None:
        return JSONResponse(status_code=400, content={"message": "無效的圖片格式"})
    
    h, w, _ = orig_img.shape
    
    # 2. 論文幾何核心：尋找主體重心
    gray = cv2.cvtColor(orig_img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (15, 15), 0)
    M = cv2.moments(blurred)
    cx, cy = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])) if M["m00"] != 0 else (w // 2, h // 2)

    ideal_x1, ideal_x2 = w // 3, (2 * w) // 3
    ideal_y1, ideal_y2 = h // 3, (2 * h) // 3
    
    # 3. 生成中文導引指令 (Text Guidance)
    instructions = []
    if cx < ideal_x1:
        instructions.append("👉【相機往右移】讓主體靠向左側三分線，畫面會更平衡。")
    elif cx > ideal_x2:
        instructions.append("👈【相機往左移】讓主體靠向右側三分線，留出視覺延伸空間。")
    else:
        instructions.append("✨ 您的水平位置不錯，主體正位於黃金分割線附近。")
            
    if cy < ideal_y1:
        instructions.append("🔽【手機向下移動 / 稍微壓低鏡頭】。")
    elif cy > ideal_y2:
        instructions.append("🔼【手機向上移動 / 稍微抬高鏡頭】。")
    else:
        instructions.append("🔍 垂直構圖高度適中，主體視覺流暢。")

    instructions.append("🔎【建議調整焦距 / 往前走近一步】排除邊緣干擾物。")

    # 4. 計算推薦裁剪框
    xmin, ymin = int(max(0, cx - (w // 4))), int(max(0, cy - (h // 4)))
    xmax, ymax = int(min(w, cx + (w // 4))), int(min(h, cy + (h // 4)))
    cropped_good_img = orig_img[ymin:ymax, xmin:xmax]
    
    # 5. 將裁剪好的照片轉為手機讀得懂的二進位檔案 (JPEG)
    _, encoded_img = cv2.imencode(".jpg", cropped_good_img)
    img_byte_arr = io.BytesIO(encoded_img.tobytes())

    # 6. 回傳給手機：包含指令 (頭部 Headers) 與 裁切後的照片 (Body)
    # 💡 這樣手機 App 就能同時拿到『文字指令』與『優化後的照片』
    headers = {
        "X-Instructions": " | ".join(instructions).encode('utf-8').decode('latin-1')
    }
    
    return StreamingResponse(img_byte_arr, media_type="image/jpeg", headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)