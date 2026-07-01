# app.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
import io
from PIL import Image, ImageStat

app = FastAPI(title="PhotoFramer Real-time API & Frontend")

# 🔥 【新增：首頁直接顯示即時相機畫面】
@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PhotoFramer 即時構圖引導系統</title>
        <style>
            body { margin: 0; background-color: #000; font-family: -apple-system, sans-serif; overflow: hidden; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; }
            #camera-container { position: relative; width: 100%; max-width: 500px; height: 70vh; background: #222; overflow: hidden; border-radius: 12px; }
            video { width: 100%; height: 100%; object-fit: cover; }
            #guidance-box { position: absolute; top: 20px; left: 5%; width: 90%; background: rgba(0, 0, 0, 0.75); color: #00ffcc; padding: 12px; border-radius: 8px; text-align: center; font-size: 16px; font-weight: bold; box-shadow: 0 4px 10px rgba(0,0,0,0.5); border: 1px solid #00ffcc; z-index: 10; transition: all 0.3s ease; }
            .grid-line { position: absolute; background: rgba(255, 255, 255, 0.3); }
            .v1 { left: 33.33%; top: 0; width: 1px; height: 100%; } .v2 { left: 66.66%; top: 0; width: 1px; height: 100%; }
            .h1 { top: 33.33%; left: 0; height: 1px; width: 100%; } .h2 { top: 66.66%; left: 0; height: 1px; width: 100%; }
            #status { color: #aaa; margin-top: 15px; font-size: 14px; text-align: center; padding: 0 10px; }
        </style>
    </head>
    <body>
        <div id="camera-container">
            <div id="guidance-box">🎥 正在啟動即時 AI 構圖導演...</div>
            <div class="grid-line v1"></div><div class="grid-line v2"></div>
            <div class="grid-line h1"></div><div class="grid-line h2"></div>
            <video id="video" autoplay playsinline></video>
        </div>
        <div id="status">系統狀態：初始化中...</div>
        <canvas id="canvas" style="display:none;"></canvas>

        <script>
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const guidanceBox = document.getElementById('guidance-box');
            const statusText = document.getElementById('status');
            const ctx = canvas.getContext('2d');

            // 💡 關鍵：因為前端網頁跟後端綁在同一個 Render 網址，這邊直接用相對路徑，完全免除網址設定！
            const API_URL = '/analyze-composition';

            navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment' }, 
                audio: false 
            })
            .then(stream => {
                video.srcObject = stream;
                statusText.innerText = "系統狀態：鏡頭已開啟，即時 AI 分析中...";
                setInterval(captureAndAnalyze, 1500); // 每 1.5 秒自動分析一次
            })
            .catch(err => {
                guidanceBox.innerText = "❌ 無法開啟相機，請檢查權限或確保使用 HTTPS 連線";
                statusText.innerText = "錯誤原因：" + err.message;
            });

            function captureAndAnalyze() {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    canvas.toBlob((blob) => {
                        if (!blob) return;
                        const formData = new FormData();
                        formData.append('file', blob, 'frame.jpg');

                        fetch(API_URL, { method: 'POST', body: formData })
                        .then(response => {
                            const rawInstructions = response.headers.get('x-instructions');
                            if (rawInstructions) {
                                const decodedInstructions = decodeURIComponent(escape(rawInstructions));
                                const mainGuidance = decodedInstructions.split('|')[0].trim();
                                guidanceBox.innerText = mainGuidance;
                            }
                        })
                        .catch(error => { console.error('連線延遲:', error); });
                    }, 'image/jpeg', 0.5); // 壓縮率 0.5 加快邊緣計算速度
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# 📸 【原本的照片分析通道保持不變】
@app.post("/analyze-composition")
async def analyze_composition(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        orig_img = Image.open(io.BytesIO(contents))
        orig_img = orig_img.convert("RGB")
    except:
        return JSONResponse(status_code=400, content={"message": "無效的圖片格式"})
    
    w, h = orig_img.size
    left_third = orig_img.crop((0, 0, w // 3, h))
    right_third = orig_img.crop(((2 * w) // 3, 0, w, h))
    
    stat_left = ImageStat.Stat(left_third).rms[0]
    stat_right = ImageStat.Stat(right_third).rms[0]
    
    instructions = []
    if stat_left > stat_right * 1.1:
        instructions.append("👈【相機往左移 / 手機稍微向左平移】（讓主體靠向右側三分線，留出視覺延伸空間）")
    elif stat_right > stat_left * 1.1:
        instructions.append("👉【相機往右移 / 手機稍微向右平移】（讓主體靠向左側三分線，畫面會更平衡）")
    else:
        instructions.append("✨ 您的水平位置不錯，主體正位於黃金分割線附近。")
            
    instructions.append("🔽【請嘗試壓低或抬高鏡頭】觀察背景干擾物是否減少。")
    instructions.append("🔎【建議調整焦距 / 往前走近一步】排除邊緣干擾物，強化視覺中心。")

    if stat_left > stat_right * 1.1:
        cx, cy = w // 3, h // 2
    elif stat_right > stat_left * 1.1:
        cx, cy = (2 * w) // 3, h // 2
    else:
        cx, cy = w // 2, h // 2

    xmin, ymin = int(max(0, cx - (w // 4))), int(max(0, cy - (h // 4)))
    xmax, ymax = int(min(w, cx + (w // 4))), int(min(h, cy + (h // 4)))
    
    cropped_good_img = orig_img.crop((xmin, ymin, xmax, ymax))
    img_byte_arr = io.BytesIO()
    cropped_good_img.save(img_byte_arr, format='JPEG')
    img_byte_arr.seek(0)

    headers = {
        "X-Instructions": " | ".join(instructions).encode('utf-8').decode('latin-1')
    }
    return StreamingResponse(img_byte_arr, media_type="image/jpeg", headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
