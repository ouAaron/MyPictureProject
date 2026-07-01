# app.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from composition_engine import AcademicCompositionEngine

app = FastAPI(title="PhotoFramer Fullscreen App")
engine = AcademicCompositionEngine()

@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>PhotoFramer AI 美學引導系統</title>
        <style>
            body { margin: 0; background-color: #000; font-family: -apple-system, sans-serif; overflow: hidden; display: flex; flex-direction: column; align-items: center; height: 100vh; color: white; -webkit-user-select: none; user-select: none; }
            
            /* 滿版相機容器，高度佔據 78% 手機螢幕長度 */
            #camera-container { position: relative; width: 100%; max-width: 500px; height: 78vh; background: #000; overflow: hidden; }
            
            /* 獨立鏡頭流縮放，三分線與外框不受影響 */
            video { width: 100%; height: 100%; object-fit: cover; transition: transform 0.25s cubic-bezier(0.1, 0.7, 0.1, 1); transform-origin: center center; }
            
            /* 提示框完美水平居中 */
            #guidance-container { position: absolute; top: 20px; left: 0; width: 100%; display: flex; justify-content: center; z-index: 20; pointer-events: none; }
            #guidance-box { width: 85%; background: rgba(0, 0, 0, 0.85); color: #00ffcc; padding: 14px 12px; border-radius: 12px; text-align: center; font-size: 14px; font-weight: bold; border: 1px solid #00ffcc; box-shadow: 0 4px 16px rgba(0,0,0,0.6); backdrop-filter: blur(6px); line-height: 1.4; box-sizing: border-box; }
            
            /* 三分法輔助線 */
            .grid-line { position: absolute; background: rgba(255, 255, 255, 0.38); z-index: 15; pointer-events: none; }
            .v1 { left: 33.33%; top: 0; width: 1.5px; height: 100%; } .v2 { left: 66.66%; top: 0; width: 1.5px; height: 100%; }
            .h1 { top: 33.33%; left: 0; height: 1.5px; width: 100%; } .h2 { top: 66.66%; left: 0; height: 1.5px; width: 100%; }
            
            /* 下方控制面板區 */
            #control-panel { width: 100%; max-width: 500px; height: 22vh; display: flex; flex-direction: column; align-items: center; justify-content: space-evenly; background: #000; z-index: 30; padding-bottom: env(safe-area-inset-bottom); }
            
            /* 幾倍數大小手動控制列（含 4.0x 功能） */
            #zoom-control-bar { display: flex; gap: 18px; margin-bottom: 2px; }
            .zoom-btn { width: 46px; height: 44px; border-radius: 20px; border: none; background: rgba(255,255,255,0.16); color: white; font-size: 11px; font-weight: bold; cursor: pointer; transition: all 0.2s ease; }
            .zoom-btn.active { background: #ffd60a; color: black; transform: scale(1.1); box-shadow: 0 0 12px #ffd60a; }
            
            /* 快門拍照按鈕 */
            #snap-btn { width: 72px; height: 72px; border-radius: 50%; background: white; border: 5px solid #222; cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
            #status { color: #8e8e93; font-size: 11px; text-align: center; letter-spacing: 0.5px; }
        </style>
    </head>
    <body>
        <div id="camera-container">
            <div id="guidance-container">
                <div id="guidance-box">系統狀態：美學引導導演正在就位...</div>
            </div>
            <div class="grid-line v1"></div><div class="grid-line v2"></div>
            <div class="grid-line h1"></div><div class="grid-line h2"></div>
            <video id="video" autoplay playsinline></video>
        </div>

        <div id="control-panel">
            <div id="zoom-control-bar">
                <button id="z1" class="zoom-btn active" onclick="setManualZoom(1.0)">1.0x</button>
                <button id="z2" class="zoom-btn" onclick="setManualZoom(2.0)">2.0x</button>
                <button id="z4" class="zoom-btn" onclick="setManualZoom(4.0)">4.0x</button>
            </div>
            <div id="status">大腦狀態：構圖美學監督中</div>
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
            let autoZoomMode = true; 

            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
            .then(stream => { video.srcObject = stream; setInterval(captureAndAnalyze, 1000); })
            .catch(err => { guidanceBox.innerText = "相機開啟失敗，請確認權限"; });

            function setManualZoom(factor) {
                autoZoomMode = false; 
                updateZoomUI(factor);
            }

            function updateZoomUI(factor) {
                currentZoom = factor;
                video.style.transform = `scale(${currentZoom})`;
                
                document.querySelectorAll('.zoom-btn').forEach(b => b.classList.remove('active'));
                
                if (factor >= 1.0 && factor < 1.8) document.getElementById('z1').classList.add('active');
                else if (factor >= 1.8 && factor < 3.2) document.getElementById('z2').classList.add('active');
                else if (factor >= 3.2) document.getElementById('z4').classList.add('active');
                
                statusText.innerText = autoZoomMode ? `AI 自動美學變焦：${factor.toFixed(1)}x` : `手動鎖定倍率：${factor.toFixed(1)}x`;
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
                            const action = response.headers.get('x-action-type');
                            
                            if (raw) {
                                guidanceBox.innerText = decodeURIComponent(escape(raw));
                                
                                if (autoZoomMode) {
                                    if (action === "zoom_in" && currentZoom < 4.0) {
                                        updateZoomUI(Math.min(4.0, currentZoom + 0.2));
                                    } else if (action === "zoom_out" && currentZoom > 1.0) {
                                        updateZoomUI(Math.max(1.0, currentZoom - 0.2));
                                    }
                                }
                            }
                        });
                    }, 'image/jpeg', 0.4);
                }
            }

            snapBtn.addEventListener('click', () => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    statusText.innerText = "正在進行幾何美學裁切並儲存相簿...";
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
                            
                            if (navigator.canShare && navigator.canShare({ files: [file] })) {
                                try {
                                    await navigator.share({ files: [file], title: '儲存優化相片' });
                                } catch (e) {}
                            } else {
                                const blobUrl = URL.createObjectURL(imageBlob);
                                const a = document.createElement('a'); a.href = blobUrl; a.download = `PhotoFramer_${Date.now()}.jpg`; a.click();
                            }
                            statusText.innerText = "大腦狀態：構圖美學監督中";
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
    output_buffer, instructions, action_type = engine.analyze(contents)
    
    if output_buffer is None:
        return JSONResponse(status_code=400, content={"message": "處理失敗"})
        
    headers = {
        "X-Instructions": instructions.encode('utf-8').decode('latin-1'),
        "X-Action-Type": action_type
    }
    return StreamingResponse(output_buffer, media_type="image/jpeg", headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
