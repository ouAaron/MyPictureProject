# main.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
import io
from PIL import Image, ImageStat

app = FastAPI(title="PhotoFramer Pure Pillow API")

@app.post("/analyze-composition")
async def analyze_composition(file: UploadFile = File(...)):
    # 1. 讀取手機傳過來的照片
    contents = await file.read()
    try:
        orig_img = Image.open(io.BytesIO(contents))
        orig_img = orig_img.convert("RGB") # 確保是 RGB 格式
    except:
        return JSONResponse(status_code=400, content={"message": "無效的圖片格式"})
    
    w, h = orig_img.size
    
    # 2. 論文幾何精神：利用 Pillow 亮度/對比重心模擬視覺焦點
    # 我們分析圖片的三分法區域，找出哪裡最吸睛
    left_third = orig_img.crop((0, 0, w // 3, h))
    right_third = orig_img.crop(((2 * w) // 3, 0, w, h))
    
    # 計算左右區域的統計資訊（模擬主體偏向）
    stat_left = ImageStat.Stat(left_third).rms[0]
    stat_right = ImageStat.Stat(right_third).rms[0]
    
    # 理想的三分線位置
    ideal_x1, ideal_x2 = w // 3, (2 * w) // 3
    
    # 3. 生成中文導引指令 (Text Guidance)
    instructions = []
    
    # 如果左邊特徵強烈，代表主體太靠左，建議手機往左平移讓主體移到右邊，反之亦然
    if stat_left > stat_right * 1.1:
        instructions.append("👈【相機往左移 / 手機稍微向左平移】（讓主體靠向右側三分線，留出視覺延伸空間）")
    elif stat_right > stat_left * 1.1:
        instructions.append("👉【相機往右移 / 手機稍微向右平移】（讓主體靠向左側三分線，畫面會更平衡）")
    else:
        instructions.append("✨ 您的水平位置不錯，主體正位於黃金分割線附近。")
            
    # 垂直建議（固定加入論文標準引導）
    instructions.append("🔽【請嘗試壓低或抬高鏡頭】觀察背景干擾物是否減少。")
    instructions.append("🔎【建議調整焦距 / 往前走近一步】排除邊緣干擾物，強化視覺中心。")

    # 4. 計算推薦裁剪框（達成 Zoom-in 效果）
    # 根據重心將視野稍微向中心或特徵點靠攏
    if stat_left > stat_right * 1.1:
        cx, cy = w // 3, h // 2
    elif stat_right > stat_left * 1.1:
        cx, cy = (2 * w) // 3, h // 2
    else:
        cx, cy = w // 2, h // 2

    xmin, ymin = int(max(0, cx - (w // 4))), int(max(0, cy - (h // 4)))
    xmax, ymax = int(min(w, cx + (w // 4))), int(min(h, cy + (h // 4)))
    
    # 裁剪
    cropped_good_img = orig_img.crop((xmin, ymin, xmax, ymax))
    
    # 5. 將裁剪好的照片轉為 JPEG 檔
    img_byte_arr = io.BytesIO()
    cropped_good_img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    # 6. 回傳給手機
    headers = {
        "X-Instructions": " | ".join(instructions).encode('utf-8').decode('latin-1')
    }
    
    return StreamingResponse(img_byte_arr, media_type="image/jpeg", headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
