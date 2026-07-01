# app.py
from fastapi import FastAPI, UploadFile, File, Header
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from composition_engine import AcademicCompositionEngine # 引入我們新蓋的演算法檔案

app = FastAPI(title="PhotoFramer Academic Camera App v4")
engine = AcademicCompositionEngine()

@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>PhotoFramer AI 美學引導系統</title>
        <style>
            body { margin: 0; background-color: #000; font-family: -apple-system, sans-serif; overflow: hidden; display: flex; flex-direction: column; align-items: center; height: 100vh; color: white; -webkit-user-select: none; user-select: none; }
            #camera-container { position: relative; width: 100%; max-width: 450px; height: 62vh; background: #000; overflow: hidden; border-radius: 16px; margin-top: 10px; }
            
            /* 🔥 【仿 iPhone 固定外框變焦】視訊畫面獨立縮放，網格永不動搖 */
            video { width: 100%; height: 100%; object-fit: cover; transition: transform 0.2s ease; transform-origin: center center; }
            
            #guidance-box { position: absolute; top: 15px; left: 5%; width: 90%; background: rgba(0, 0, 0, 0.85); color: #00ffcc; padding: 12px 8px; border-radius: 10px; text-align: center; font-size: 14px; font-weight: bold; border: 1px solid #00ffcc; z-index: 20; }
            .grid-line { position: absolute; background: rgba(255, 255, 255, 0.4); z-index: 15; pointer-events: none; }
            .v1 { left: 33.33%; top: 0; width: 1.5px; height: 100%; } .v2 { left: 66.66%; top: 0; width: 1.5px; height: 100%; }
            .h1 { top: 33.33%; left: 0; height: 1.5px; width: 100%; } .h2 { top: 66.66%; left: 0; height: 1.5px; width: 100%; }
            
            /* 控制面板 */
            #control-panel { width: 100%; max-width: 450px; height: 28vh; display: flex; flex-direction: column; align-items: center; justify-content: space-evenly; background: #000; }
            
            /* 🔥 【新增功能】：iPhone 級手動切換倍率按鈕列 */
            #zoom-control-bar { display: flex; gap: 15px; margin-bottom: 5px; }
            .zoom-btn { width: 42px; height: 42px; border-radius: 50%; border: none; background: rgba(255,255,255,0.15); color: white; font-size: 12px; font-weight: bold; cursor: pointer; transition: all 0.2s; }
            .zoom-btn.active { background: #ffd60a; color: black; transform: scale(1.1); }
            
            #snap-btn { width: 74px; height: 74px; border-radius: 50%; background: white; border: 6px solid #333; cursor: pointer; }
            #status { color: #8e8e93; font-size: 12px; text-align: center; }
        </style>
    </head>
    <body>
        <div id="camera-container">
            <div id="guidance-box">系統狀態：初始化 AI 構圖引源核心...</div>
            <div class="grid-line v1"></div><div class="grid-line v2"></div>
            <div class="grid-line h1"></div><div class="grid-line h2"></div>
            <video id="video" autoplay playsinline></video>
        </div>

        <div id="control-panel">
            <div id="zoom-control-bar">
                <button class="zoom-btn active" onclick="setManualZoom(1.0, this)">1.0x</button>
                <button class="zoom-btn" onclick="setManualZoom(2.0, this)">2.0x</button>
                <button class="zoom-btn" onclick="setManualZoom(3.0, this)">3.0x</button>
            </div>
            <div id="status">大腦連線狀態：美學監督中</div>
            <button id="snap-btn"></button>
        </div>

        <canvas id="canvas" style="display:none;"></canvas>

        <script>
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const guidanceBox = document.getElementById('guidance-box');
            const statusText = document.getElementById('status');
            const snapBtn = document.getElementById('snap-btn');
            const ctx = canvas.getContext('2d');

            let currentZoom = 1.0; 
            let autoZoomEnabled = true; // 當使用者沒手動點擊時，允許 AI 自動建議變焦

            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
            .then(stream => { video.srcObject = stream; setInterval(captureAndAnalyze, 1200); })
            .catch(err => { guidanceBox.innerText = "相機啟動失敗"; });

            // 🔥 【新增功能】：手動點擊 1.0x/2.0x/3.0x 調整畫面倍數
            function setManualZoom(factor, element) {
                autoZoomEnabled = false; // 使用者主動介入，暫停 AI 自動縮放，完全聽使用者的命令
                currentZoom = factor;
                video.style.transform = `scale(${currentZoom})`;
                
                // 切換按鈕亮燈樣式
                document.querySelectorAll('.zoom-btn').forEach(btn => btn.classList.remove('active'));
                element.classList.add('active');
                statusText.innerText = `手動變焦控制：${factor.toFixed(1)}x`;
            }

            function captureAndAnalyze() {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    canvas.width = 240;
                    canvas.height = (video.videoHeight / video.videoWidth) * 240;
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    canvas.toBlob((blob) => {
                        if (!blob) return;
                        const formData = new FormData();
                        formData.append('file', blob, 'stream.jpg');

                        fetch('/analyze-composition', { method: 'POST', body: formData })
                        .then(response => {
                            const raw = response.headers.get('x-instructions');
                            const action = response.headers.get('x-action-type'); // 拿回動作訊號
                            
                            if (raw) {
                                guidanceBox.innerText = decodeURIComponent(escape(raw));
                                
                                // 如果使用者目前處於自動模式，且 AI 大腦建議需要縮放 Z 軸
                                if (autoZoomEnabled) {
                                    if (action === "zoom_in" && currentZoom < 2.5) {
                                        currentZoom += 0.1;
                                    } else if (action === "zoom_out" && currentZoom > 1.0) {
                                        currentZoom -= 0.1;
                                    }
                                    video.style.transform = `scale(${currentZoom})`;
                                }
                            }
                        });
                    }, 'image/jpeg', 0.4);
                }
            }

            // 📸 拍照並透過 Web Share API 存入手機原生相簿庫
            snapBtn.addEventListener('click', () => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    statusText.innerText = "正在進行論文級優化並寫入相簿...";
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    
                    ctx.save();
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

                        fetch('/analyze-composition', { method: 'POST', body: formData })
                        .then(response => response.blob())
                        .then(async (imageBlob) => {
                            const file = new File([imageBlob], `PhotoFramer_${Date.now()}.jpg`, { type: 'image/jpeg' });
                            
                            // 🔥 【寫入手機相簿核心】：調用系統原生分享選單，點選「儲存影像」即入相簿庫
                            if (navigator.canShare && navigator.canShare({ files: [file] })) {
                                try {
                                    await navigator.share({ files: [file], title: '儲存相片' });
                                } catch (e) {}
                            } else {
                                const blobUrl = URL.createObjectURL(imageBlob);
                                const a = document.createElement('a'); a.href = blobUrl; a.download = `PhotoFramer_${Date.now()}.jpg`; a.click();
                            }
                            statusText.innerText = "相片處置完畢";
                        });
                    }, 'image/jpeg', 0.95);
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/analyze-composition")
async def analyze_composition(file: UploadFile = File(...)):
    contents = await file.read()
    # 呼叫我們拆分出去的全新 .py 模組大腦
    output_buffer, instructions, action_type = engine.analyze(contents)
    
    if output_buffer is None:
        return JSONResponse(status_code=400, content={"message": "處理失敗"})
        
    headers = {
        "X-Instructions": instructions.encode('utf-8').decode('latin-1'),
        "X-Action-Type": action_type # 把動作類型也傳給前端
    }
    return StreamingResponse(output_buffer, media_type="image/jpeg", headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
