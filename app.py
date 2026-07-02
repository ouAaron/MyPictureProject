# app.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from composition_engine import AcademicCompositionEngine

app = FastAPI(title="PhotoFramer Zero-Latency Camera")
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
            video { width: 100%; height: 100%; object-fit: cover; }
            
            #guidance-container { position: absolute; top: 15px; left: 0; width: 100%; display: flex; justify-content: center; z-index: 20; pointer-events: none; }
            #guidance-box { width: 88%; background: rgba(0, 0, 0, 0.7); color: #ffd60a; padding: 10px 14px; border-radius: 20px; text-align: center; font-size: 13px; font-weight: bold; border: 1px solid rgba(255, 214, 10, 0.5); box-shadow: 0 4px 12px rgba(0,0,0,0.4); backdrop-filter: blur(10px); line-height: 1.4; box-sizing: border-box; }
            
            .grid-line { position: absolute; background: rgba(255, 255, 255, 0.25); z-index: 15; pointer-events: none; }
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
            <span style="font-size:12px; font-weight:700; color:#ffd60a; letter-spacing:1px;">🟢 iPhone PURE CAMERA</span>
            <span class="top-icon">⚙️</span>
        </div>

        <div id="camera-container">
            <div id="guidance-container">
                <div id="guidance-box">請對準主體，按下快門自動進行黃金比例優化</div>
            </div>
            
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
            <div id="status">極速原生串流已就緒</div>
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

            // 🪐 拍照前百分之百純原生流，完全不執行定時 captureAndAnalyze，提速 100%
            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
            .then(stream => { video.srcObject = stream; }) 
            .catch(err => { guidanceBox.innerText = "相機啟動失敗"; });

            function setManualZoom(factor) {
                currentZoom = factor;
                video.style.transform = `scale(${currentZoom})`;
                document.querySelectorAll('.zoom-btn').forEach(b => b.classList.remove('active'));
                if (factor === 1.0) document.getElementById('z1').classList.add('active');
                else if (factor === 2.0) document.getElementById('z2').classList.add('active');
                else if (factor === 4.0) document.getElementById('z4').classList.add('active');
            }

            // 🪐 只有在按下快門的一瞬間，才將相片送至後端進行高級美學不對稱裁切
            snapBtn.addEventListener('click', () => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    statusText.innerText = "正在進行智慧美學裁切...";
                    
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
                            statusText.innerText = "相片優化完成並已儲存";
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
    
    headers = {
        "X-Instructions": instructions.encode('utf-8').decode('latin-1'),
        "X-Action-Type": action_type
    }
    return StreamingResponse(output_buffer, media_type="image/jpeg", headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
