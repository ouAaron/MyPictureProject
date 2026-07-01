# app.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
import io
from PIL import Image, ImageStat

app = FastAPI(title="PhotoFramer Academic Camera App v3")

# 🎬 前端網頁：實現 iPhone 級固定網格變焦與原生相簿儲存機制
@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>PhotoFramer AI 構圖美學引導系統</title>
        <style>
            body { margin: 0; background-color: #000; font-family: -apple-system, sans-serif; overflow: hidden; display: flex; flex-direction: column; align-items: center; height: 100vh; color: white; -webkit-user-select: none; user-select: none; }
            
            /* 1. 外層容器固定大小 */
            #camera-container { position: relative; width: 100%; max-width: 450px; height: 65vh; background: #000; overflow: hidden; border-radius: 16px; margin-top: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.6); }
            
            /* 🔥 【關鍵修正】：視訊畫面獨立控制，放大時只放大視訊，外層框與輔助線絕不動搖 */
            video { width: 100%; height: 100%; object-fit: cover; transition: transform 0.2s ease; transform-origin: center center; }
            
            /* 專業導演引導字幕框（絕對定位，不受 video 放大影響） */
            #guidance-box { position: absolute; top: 15px; left: 5%; width: 90%; background: rgba(0, 0, 0, 0.85); color: #00ffcc; padding: 12px 8px; border-radius: 10px; text-align: center; font-size: 14px; font-weight: bold; border: 1px solid #00ffcc; z-index: 20; box-shadow: 0 4px 12px rgba(0,0,0,0.5); pointer-events: none; }
            
            /* 🔥 【關鍵修正】：三分法輔助線階層提高(z-index: 15)，永遠固定，寬度維持 1.5px 不變粗 */
            .grid-line { position: absolute; background: rgba(255, 255, 255, 0.4); z-index: 15; pointer-events: none; }
            .v1 { left: 33.33%; top: 0; width: 1.5px; height: 100%; } .v2 { left: 66.66%; top: 0; width: 1.5px; height: 100%; }
            .h1 { top: 33.33%; left: 0; height: 1.5px; width: 100%; } .h2 { top: 66.66%; left: 0; height: 1.5px; width: 100%; }
            
            /* 控制面板與快門鍵 */
            #control-panel { width: 100%; max-width: 450px; height: 25vh; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #000; z-index: 30; }
            #snap-btn { width: 74px; height: 74px; border-radius: 50%; background: white; border: 6px solid #333; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.4); transition: transform 0.1s; }
            #snap-btn:active { transform: scale(0.92); }
            #status { color: #8e8e93; font-size: 13px; margin-bottom: 12px; text-align: center; }
            
            /* 數位變焦倍率顯示數值（仿 iPhone 介面） */
            #zoom-indicator { color: #ffd60a; font-size: 12px; font-weight: bold; margin-bottom: 8px; background: rgba(255,255,255,0.15); padding: 3px 8px; border-radius: 10px; display: none; }
        </style>
    </head>
    <body>
        <div id="camera-container">
            <div id="guidance-box">系統狀態：初始化 AI 構圖引導核心...</div>
            <div class="grid-line v1"></div><div class="grid-line v2"></div>
            <div class="grid-line h1"></div><div class="grid-line h2"></div>
            <video id="video" autoplay playsinline></video>
        </div>

        <div id="control-panel">
            <div id="zoom-indicator">1.0x</div>
            <div id="status">大腦連線狀態：準備中</div>
            <button id="snap-btn"></button>
        </div>

        <canvas id="canvas" style="display:none;"></canvas>

        <script>
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const guidanceBox = document.getElementById('guidance-box');
            const statusText = document.getElementById('status');
            const snapBtn = document.getElementById('snap-btn');
            const zoomIndicator = document.getElementById('zoom-indicator');
            const ctx = canvas.getContext('2d');

            const API_URL = '/analyze-composition';
            
            // 當前畫面的數位放大倍率變數
            let currentZoom = 1.0; 

            // 1. 啟動相機鏡頭
            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
            .then(stream => {
                video.srcObject = stream;
                statusText.innerText = "系統狀態：美學引導中";
                setInterval(captureAndAnalyze, 1200); // 週期性傳送串流分析
            })
            .catch(err => {
                guidanceBox.innerText = "錯誤：相機啟動失敗，請檢查權限";
            });

            // 2. 即時分析並控制「仿 iPhone 的畫面變焦」
            function captureAndAnalyze() {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    canvas.width = 240;
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
                                const instructionString = decoded.split('|')[0].trim();
                                guidanceBox.innerText = instructionString;
                                
                                // 🔥 【核心變更：配合大腦引導，動態調整 video 的 CSS 縮放，而框與線完全不動！】
                                if (instructionString.includes("放大焦距") || instructionString.includes("前進")) {
                                    if (currentZoom < 1.8) currentZoom += 0.1; // 逐步放大鏡頭背景
                                    video.style.transform = `scale(${currentZoom})`;
                                    zoomIndicator.innerText = `${currentZoom.toFixed(1)}x`;
                                    zoomIndicator.style.display = "block";
                                } else if (instructionString.includes("縮小焦距") || instructionString.includes("後退")) {
                                    if (currentZoom > 1.0) currentZoom -= 0.1; // 逐步縮小鏡頭背景
                                    video.style.transform = `scale(${currentZoom})`;
                                    zoomIndicator.innerText = `${currentZoom.toFixed(1)}x`;
                                    zoomIndicator.style.display = currentZoom > 1.0 ? "block" : "none";
                                }
                            }
                        })
                        .catch(err => { console.error(err); });
                    }, 'image/jpeg', 0.4);
                }
            }

            // 3. 📸 核心變更：拍照按鈕觸發後，利用原生分享選單 100% 存入手機相簿
            snapBtn.addEventListener('click', () => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    statusText.innerText = "正在儲存並優化構圖中...";
                    
                    // 拍照時要把當前數位變焦後的畫面真實擷取下來
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    
                    ctx.save();
                    // 讓畫布跟著當前變焦比例做裁切繪製，確保拍出來的圖就是看見的變焦效果
                    if (currentZoom > 1.0) {
                        ctx.translate(canvas.width / 2, canvas.height / 2);
                        ctx.scale(currentZoom, currentZoom);
                        ctx.translate(-canvas.width / 2, -canvas.height / 2);
                    }
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    ctx.restore();
                    
                    canvas.toBlob((blob) => {
                        if (!blob) return;
                        const formData = new FormData();
                        formData.append('file', blob, 'capture.jpg');

                        fetch(API_URL, { method: 'POST', body: formData })
                        .then(response => response.blob())
                        .then(async (imageBlob) => {
                            statusText.innerText = "系統狀態：美學引導中";
                            
                            // 將二進位 Blob 轉換為真實的實體檔案物件
                            const file = new File([imageBlob], `PhotoFramer_${Date.now()}.jpg`, { type: 'image/jpeg' });
                            
                            // 🔥 【學術/應用核心】：呼叫手機原生 Web Share API 彈出選單
                            if (navigator.canShare && navigator.canShare({ files: [file] })) {
                                try {
                                    await navigator.share({
                                        files: [file],
                                        title: '儲存優化相片',
                                        text: 'PhotoFramer AI 構圖美學成果'
                                    });
                                    // 使用者此時在手機跳出的選單點擊「儲存影像」即可完美寫入手機相簿圖庫！
                                } catch (error) {
                                    console.log('使用者取消分享/儲存');
                                }
                            } else {
                                // 備用方案：若不支援則觸發網頁下載
                                const blobUrl = URL.createObjectURL(imageBlob);
                                const downloadLink = document.createElement('a');
                                downloadLink.href = blobUrl;
                                downloadLink.download = `PhotoFramer_${Date.now()}.jpg`;
                                downloadLink.click();
                            }
                        })
                        .catch(err => {
                            alert("拍攝失敗: " + err);
                        });
                    }, 'image/jpeg', 0.95);
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# 🧠 後端大腦：維持嚴格判定指標
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
    center_core = orig_img.crop((w // 4, h // 4, (3 * w) // 4, (3 * h) // 4))
    
    stat_left = ImageStat.Stat(left_third).rms[0]
    stat_right = ImageStat.Stat(right_third).rms[0]
    stat_center = ImageStat.Stat(center_core).rms[0]
    stat_global = ImageStat.Stat(orig_img).rms[0]
    
    instructions = []
    imbalance_threshold = 1.05 
    
    if stat_left > stat_right * imbalance_threshold:
        instructions.append("[請向左平移鏡頭] 修正當前主體偏右情形，使視覺特徵靠向黃金分割線位置")
    elif stat_right > stat_left * imbalance_threshold:
        instructions.append("[請向右平移鏡頭] 修正當前主體偏左情形，使視覺特徵靠向黃金分割線位置")
    else:
        # 當水平平衡時，由大腦判斷是否給予 Z 軸變焦提示
        if stat_center < stat_global * 0.9:
            instructions.append("[建議前進或放大焦距] 核心特徵占比過低，建議縮減環境冗餘邊緣")
        elif stat_center > stat_global * 1.15:
            instructions.append("[建議後退或縮小焦距] 視覺主體壓迫感過強，建議保留畫面呼吸空間")
        else:
            instructions.append("構圖指標已達美學標準，可直接按下拍攝鈕")

    if stat_left > stat_right * imbalance_threshold:
        cx, cy = w // 3, h // 2
    elif stat_right > stat_left * imbalance_threshold:
        cx, cy = (2 * w) // 3, h // 2
    else:
        cx, cy = w // 2, h // 2

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
