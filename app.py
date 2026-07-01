# app.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
import io
from PIL import Image, ImageStat

app = FastAPI(title="PhotoFramer Real-time Camera App")

# 🎬 前端網頁：包含即時引導網格、相機、拍照鍵、AI裁切成果彈窗
@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PhotoFramer AI 即時美學引導系統</title>
        <style>
            body { margin: 0; background-color: #121212; font-family: -apple-system, sans-serif; overflow: hidden; display: flex; flex-direction: column; align-items: center; height: 100vh; color: white; }
            #camera-container { position: relative; width: 100%; max-width: 450px; height: 65vh; background: #000; overflow: hidden; border-radius: 16px; margin-top: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.6); }
            video { width: 100%; height: 100%; object-fit: cover; }
            
            /* 導演導引字幕 */
            #guidance-box { position: absolute; top: 15px; left: 5%; width: 90%; background: rgba(0, 0, 0, 0.8); color: #00ffcc; padding: 12px 8px; border-radius: 10px; text-align: center; font-size: 15px; font-weight: bold; border: 1px solid #00ffcc; z-index: 10; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
            
            /* 三分法輔助線 */
            .grid-line { position: absolute; background: rgba(255, 255, 255, 0.35); }
            .v1 { left: 33.33%; top: 0; width: 1.5px; height: 100%; } .v2 { left: 66.66%; top: 0; width: 1.5px; height: 100%; }
            .h1 { top: 33.33%; left: 0; height: 1.5px; width: 100%; } .h2 { top: 66.66%; left: 0; height: 1.5px; width: 100%; }
            
            /* 下方控制區與拍照鈕 */
            #control-panel { width: 100%; max-width: 450px; height: 25vh; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #121212; }
            #snap-btn { width: 76px; height: 76px; border-radius: 50%; background: white; border: 6px solid #333; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.4); transition: all 0.2s; }
            #snap-btn:active { transform: scale(0.9); background: #ff3b30; }
            #status { color: #8e8e93; font-size: 13px; margin-bottom: 15px; text-align: center; }

            /* 拍照成功彈出視窗 (Modal) */
            #result-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 100; flex-direction: column; align-items: center; justify-content: center; }
            #result-img { max-width: 90%; max-height: 65vh; border-radius: 12px; border: 2px solid #fff; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            #modal-close-btn { margin-top: 25px; padding: 12px 30px; background: #007aff; color: white; border: none; border-radius: 25px; font-size: 16px; font-weight: bold; cursor: pointer; }
        </style>
    </head>
    <body>
        <div id="camera-container">
            <div id="guidance-box">🎥 初始化 AI 構圖導演系統...</div>
            <div class="grid-line v1"></div><div class="grid-line v2"></div>
            <div class="grid-line h1"></div><div class="grid-line h2"></div>
            <video id="video" autoplay playsinline></video>
        </div>

        <div id="control-panel">
            <div id="status">大腦訊號：連線中...</div>
            <button id="snap-btn" title="拍照"></button>
        </div>

        <div id="result-modal">
            <h3 style="color: #00ffcc; margin-bottom: 10px;">✨ AI 論文黃金比例裁切成果</h3>
            <img id="result-img" src="" alt="AI Optimized Image">
            <button id="modal-close-btn" onclick="closeModal()">返回繼續拍攝</button>
        </div>

        <canvas id="canvas" style="display:none;"></canvas>

        <script>
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const guidanceBox = document.getElementById('guidance-box');
            const statusText = document.getElementById('status');
            const snapBtn = document.getElementById('snap-btn');
            const resultModal = document.getElementById('result-modal');
            const resultImg = document.getElementById('result-img');
            const ctx = canvas.getContext('2d');

            const API_URL = '/analyze-composition';

            // 1. 開啟相機
            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
            .then(stream => {
                video.srcObject = stream;
                statusText.innerText = "系統狀態：AI 導演已進駐觀景窗";
                setInterval(captureAndAnalyze, 1200); // 每 1.2 秒即時偵測更新引導
            })
            .catch(err => {
                guidanceBox.innerText = "❌ 相機啟動失敗，請確認 HTTPS 權限";
                statusText.innerText = "錯誤: " + err.message;
            });

            // 2. 背景即時發送串流畫格（只拿 Headers 指令）
            function captureAndAnalyze() {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    canvas.width = 240; // 降低串流解析度，極速降低網路延遲
                    canvas.height = (video.videoHeight / video.videoWidth) * 240;
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    canvas.toBlob((blob) => {
                        if (!blob) return;
                        const formData = new FormData();
                        formData.append('file', blob, 'stream.jpg');

                        fetch(API_URL, { method: 'POST', body: formData })
                        .then(response => {
                            const raw = response.headers.get('x-instructions');
                            if (raw) {
                                const decoded = decodeURIComponent(escape(raw));
                                // 抓取第一條最核心的即時物理移動引導
                                guidanceBox.innerText = decoded.split('|')[0].trim();
                            }
                        })
                        .catch(err => { console.error(err); });
                    }, 'image/jpeg', 0.4);
                }
            }

            // 3. 📸 拍照按鈕點擊：上傳高畫質照片，並當場下載 AI 裁切優化圖
            snapBtn.addEventListener('click', () => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    statusText.innerText = "⚡ 正在捕捉高畫質影像並進行黃金比例裁切...";
                    
                    // 擷取原比例高畫質
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    canvas.toBlob((blob) => {
                        if (!blob) return;
                        const formData = new FormData();
                        formData.append('file', blob, 'capture.jpg');

                        // 發送給後端，這次要拿回 Response Body 的圖片
                        fetch(API_URL, { method: 'POST', body: formData })
                        .then(response => response.blob())
                        .then(imageBlob => {
                            const blobUrl = URL.createObjectURL(imageBlob);
                            resultImg.src = blobUrl; // 將 AI 裁切完的圖放入隱藏彈窗
                            resultModal.style.display = 'flex'; // 彈窗秀出來！
                            statusText.innerText = "🎉 構圖優化成功！";
                        })
                        .catch(err => {
                            alert("拍照優化失敗: " + err);
                            statusText.innerText = "狀態：拍攝連線失敗";
                        });
                    }, 'image/jpeg', 0.9);
                }
            });

            function closeModal() {
                resultModal.style.display = 'none';
                statusText.innerText = "系統狀態：AI 導演已進駐觀景窗";
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# 🧠 後端大腦：全面升級論文「幾何與特徵密度演算法」
@app.post("/analyze-composition")
async def analyze_composition(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        orig_img = Image.open(io.BytesIO(contents))
        orig_img = orig_img.convert("RGB")
    except:
        return JSONResponse(status_code=400, content={"message": "無效的圖片格式"})
    
    w, h = orig_img.size
    
    # 論文多區域切片分析：左、右、以及中央黃金核心區
    left_third = orig_img.crop((0, 0, w // 3, h))
    right_third = orig_img.crop(((2 * w) // 3, 0, w, h))
    center_core = orig_img.crop((w // 4, h // 4, (3 * w) // 4, (3 * h) // 4))
    
    # 計算各區域的 Root Mean Square 統計量（特徵能量密度）
    stat_left = ImageStat.Stat(left_third).rms[0]
    stat_right = ImageStat.Stat(right_third).rms[0]
    stat_center = ImageStat.Stat(center_core).rms[0]
    stat_global = ImageStat.Stat(orig_img).rms[0]
    
    instructions = []
    
    # 🎯 1. 左右維度引導 (X-axis)
    if stat_left > stat_right * 1.15:
        instructions.append("👈【手機稍微向左平移】（讓主體靠向右側三分線，留出視覺延伸空間）")
    elif stat_right > stat_left * 1.15:
        instructions.append("👉【手機稍微向右平移】（讓主體靠向左側三分線，畫面會更平衡）")
    else:
        # 🎯 2. 深度維度引導 (Z-axis) - 只有當左右相對平衡時，深度導引才浮現
        if stat_center < stat_global * 0.85:
            instructions.append("🔎【請往前走近一步 / 放大焦距 Zoom-in】（主體在中央過於渺小，請凸顯視覺焦點）")
        elif stat_center > stat_global * 1.25:
            instructions.append("🚶【請稍微往後退一步 / 縮小焦距 Zoom-out】（畫面太滿、壓迫感較重，請保留呼吸空間）")
        else:
            instructions.append("✨ 構圖非常完美！請直接按下下方拍照鍵！")

    # 推薦裁剪重心定位
    if stat_left > stat_right * 1.15:
        cx, cy = w // 3, h // 2
    elif stat_right > stat_left * 1.15:
        cx, cy = (2 * w) // 3, h // 2
    else:
        cx, cy = w // 2, h // 2

    # 計算推薦裁剪框（進行黃金比例 Zoom-in）
    xmin, ymin = int(max(0, cx - (w // 3.5))), int(max(0, cy - (h // 3.5)))
    xmax, ymax = int(min(w, cx + (w // 3.5))), int(min(h, cy + (h // 3.5)))
    
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
