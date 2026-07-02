# app.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from composition_engine import AcademicCompositionEngine

app = FastAPI(title="PhotoFramer Real-time Pure Camera")
engine = AcademicCompositionEngine()

@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
        <title>Camera</title>
        <style>
            body { margin: 0; background-color: #000; font-family: -apple-system, sans-serif; overflow: hidden; display: flex; flex-direction: column; align-items: center; height: 100vh; color: white; -webkit-user-select: none; user-select: none; }
            #top-bar { width: 100%; max-width: 500px; height: 6vh; background-color: #000; display: flex; align-items: center; justify-content: space-between; padding: 0 20px; box-sizing: border-box; }
            
            #camera-container { position: relative; width: 100%; max-width: 500px; height: 72vh; background: #000; overflow: hidden; }
            video { width: 100%; height: 100%; object-fit: cover; transition: transform 0.25s ease; transform-origin: center center; }
            
            #guidance-container { position: absolute; top: 15px; left: 0; width: 100%; display: flex; justify-content: center; z-index: 20; pointer-events: none; }
            #guidance-box { width: 88%; background: rgba(0, 0, 0, 0.7); color: #00ffcc; padding: 10px 14px; border-radius: 20px; text-align: center; font-size: 13px; font-weight: bold; border: 1px solid rgba(0, 255, 204, 0.6); box-shadow: 0 4px 12px rgba(0,0,0,0.4); backdrop-filter: blur(10px); line-height: 1.4; box-sizing: border-box; }
            
            .nav-arrow { position: absolute; top: 42%; width: 50px; height: 80px; background: rgba(0,0,0,0.2); z-index: 25; display: flex; align-items: center; justify-content: center; font-size: 32px; color: rgba(255,255,255,0.12); border-radius: 8px; font-weight: bold; pointer-events: none; transition: all 0.2s ease; }
            #arrow-left { left: 10px; }
            #arrow-right { right: 10px; }
            .nav-arrow.active { color: #00ffcc; background: rgba(0, 255, 204, 0.15); border: 1px solid #00ffcc; box-shadow: 0 0 15px #00ffcc; text-shadow: 0 0 8px #00ffcc; transform: scale(1.05); }
            
            .grid-line { position: absolute; background: rgba(255, 255, 255, 0.3); z-index: 15; pointer-events: none; }
            .v1 { left: 33.33%; top: 0; width: 1px; height: 100%; } .v2 { left: 66.66%; top: 0; width: 1px; height: 100%; }
            .h1 { top: 33.33%; left: 0; height: 1px; width: 100%; } .h2 { top: 66.66%; left: 0; height: 1px; width: 100%; }
            
            #control-panel { width: 100%; max-width: 500px; height: 22vh; display: flex; flex-direction: column; align-items: center; justify-content: space-evenly; background: #000; z-index: 30; padding-bottom: env(safe-area-inset-bottom); }
            #zoom-control-bar { display: flex; gap: 16px; align-items: center; background: rgba(255, 255, 255, 0.08); padding: 4px 14px; border-radius: 20px; }
            .zoom-btn { background: none; border: none; color: #e5e5ea; font-size: 11px; font-weight: 600; cursor: pointer; padding: 4px 6px; border-radius: 50%; }
            .zoom-btn.active { color: #ffd60a; transform: scale(1.15); font-weight: 700; }
            #mode-selector { color: #ffd60a; font-size: 12px; font-weight: 600; letter-spacing: 1px; }
            #shutter-container { display: flex; align-items: center; justify-content: center; width: 100%; }
            #snap-btn { width: 66px; height: 66px; border-radius: 50%; background: #fff; border: 4px solid #000; box-shadow: 0 0 0 4px #fff; cursor: pointer; }
            #status { color: #8e8e93; font-size: 10px; text-align: center; }
        </style>
    </head>
    <body>
        <div id="top-bar">
            <span class="top-icon">⚡</span>
            <span style="font-size:12px; font-weight:700; color:#ffd60a; letter-spacing:1px;">🟢 AI OVERSIGHT LIVE</span>
            <span class="top-icon">⚙️</span>
        </div>

        <div id="camera-container">
            <div id="guidance-container">
                <div id="guidance-box">正在即時分析畫面幾何...</div>
            </div>
            
            <div id="arrow-left" class="nav-arrow">◀</div>
            <div id="arrow-right" class="nav-arrow">▶</div>
            
            <div class="grid-line v1"></div><div class="grid-line v2"></div>
            <div class="grid-line h1"></div><div class="grid-line h2"></div>
            <video id="video" autoplay playsinline></video>
        </div>

        <div id="control-panel">
            <div id="zoom-control-bar">
                <button id="z1" class="zoom-btn active" onclick="setManualZoom(1.0)">1x</button>
                <button id="z2" class="zoom-btn" onclick="setManualZoom(2.0)">2x</button>
                <button id="z4" class="zoom-btn" onclick="setManualZoom(4.0)">4x</button>
            </div>
            <div id="mode-selector">照片</div>
            <div id="shutter-container"><button id="snap-btn"></button></div>
            <div id="status">即時物理美學引導流已開啟</div>
        </div>

        <canvas id="canvas" style="display:none;"></canvas>

        <script>
            const video = document.getElementById('video');
            const canvas = document.getElementById('canvas');
            const guidanceBox = document.getElementById('guidance-box');
            const statusText = document.getElementById('status');
            const snapBtn = document.getElementById('snap-btn');
            const arrowLeft = document.getElementById('arrow-left');
            const arrowRight = document.getElementById('arrow-right');
            const ctx = canvas.getContext('2d');

            let currentZoom = 1.0;
            let autoZoomMode = true; 

            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
            .then(stream => { video.srcObject = stream; setInterval(captureAndAnalyze, 750); }) 
            .catch(err => { guidanceBox.innerText = "相機啟動失敗"; });

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
                                const decoded = decodeURIComponent(escape(raw));
                                const parts = decoded.split('@');
                                // 直接過濾掉零件標籤，只抓純指令
                                const instructionText = parts[1] ? parts[1] : parts[0];

                                guidanceBox.innerText = instructionText;
                                
                                arrowLeft.classList.remove('active');
                                arrowRight.classList.remove('active');
                                
                                if (action === "left") arrowLeft.classList.add('active');
                                else if (action === "right") arrowRight.classList.add('active');
                                
                                if (autoZoomMode) {
                                    if (action === "zoom_in" && currentZoom < 4.0) updateZoomUI(Math.min(4.0, currentZoom + 0.2));
                                    else if (action === "zoom_out" && currentZoom > 1.0) updateZoomUI(Math.max(1.0, currentZoom - 0.2));
                                }
                            }
                        });
                    }, 'image/jpeg', 0.4);
                }
            }

            snapBtn.addEventListener('click', () => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    statusText.innerText = "正在儲存優化照片...";
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
                                try { await navigator.share({ files: [file], title: '儲存優化相片' }); } catch (e) {}
                            } else {
                                const blobUrl = URL.createObjectURL(imageBlob);
                                const a = document.createElement('a'); a.href = blobUrl; a.download = `PhotoFramer_${Date.now()}.jpg`; a.click();
                            }
                            statusText.innerText = "相片已成功處置";
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
