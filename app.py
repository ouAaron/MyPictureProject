import os
import math
import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from composition_engine import AcademicCompositionEngine

# =====================================================================
# 🔗 【Roboflow 雲端模型自動下載設定區】
# =====================================================================
ROBOFLOW_API_KEY = "uutYOvhpEyTSgKugglI9"  # 👈 你的 API Key
PROJECT_NAME = "你的專案名稱"                # 👈 ⚙️ 爸，記得把這裡改成你在 Roboflow 的 Project ID (網址列上看得到)
PROJECT_VERSION = 1                       # 👈 ⚙️ 記得改成你剛剛訓練完的最新版本號 (例如 1, 2, 3)

MODEL_DIR = f"./{PROJECT_NAME}-{PROJECT_VERSION}"
MODEL_PATH = os.path.join(MODEL_DIR, "weights", "best.pt")

app = FastAPI(title="PhotoFramer Multi-modal Camera")
engine = AcademicCompositionEngine()

# 💡 宣告全域模型變數
model = None

@app.on_event("startup")
def load_cloud_model():
    global model
    print("📢 正在檢查後端 AI 大腦狀態...")
    
    if not os.path.exists(MODEL_PATH):
        print(f"📥 偵測到首次開機，正在透過 API 從 Roboflow 下載模型: {PROJECT_NAME} v{PROJECT_VERSION}")
        try:
            from roboflow import Roboflow
            rf = Roboflow(api_key=ROBOFLOW_API_KEY)
            project = rf.workspace().project(PROJECT_NAME)
            # 下載 yolov8 格式的模型權重
            dataset = project.version(PROJECT_VERSION).download("yolov8")
            print("✅ Roboflow 模型權重下載成功！")
        except Exception as e:
            print(f"❌ 從 Roboflow 下載模型失敗: {e}. 請確認 PROJECT_NAME 是否正確。")
    else:
        print("✅ 偵測到已有現存模型，跳過下載。")
    
    # 🎯 載入下載好的 YOLO 預測模型
    try:
        from ultralytics import YOLO
        # Roboflow 下載下來的權重通常會在這個路徑
        actual_path = MODEL_PATH if os.path.exists(MODEL_PATH) else "best.pt"
        model = YOLO(actual_path)
        print(f"🚀 YOLOv8 Horizon 模型載入成功！路徑: {actual_path}")
    except Exception as e:
        print(f"⚠️ 載入 YOLO 模型失敗: {e}")

# =====================================================================
# 🖥️ 【前端相機網頁介面】（維持高清與低延遲拆分架構）
# =====================================================================
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
            .nav-arrow { position: absolute; top: 42%; width: 50px; height: 80px; background: rgba(0,0,0,0.3); z-index: 25; display: flex; align-items: center; justify-content: center; font-size: 32px; color: #00ffcc; border-radius: 8px; font-weight: bold; pointer-events: none; opacity: 0; transition: opacity 0.2s ease; }
            #arrow-left { left: 10px; } #arrow-right { right: 10px; }
            .nav-arrow.active { opacity: 0.3; border: 1px solid #00ffcc; box-shadow: 0 0 10px #00ffcc; }
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
            <div id="guidance-container"><div id="guidance-box">正在即時分析畫面幾何...</div></div>
            <div id="arrow-left" class="nav-arrow">◀</div><div id="arrow-right" class="nav-arrow">▶</div>
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
            <div id="status">即時自適應引導串流中</div>
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

            navigator.mediaDevices.getUserMedia({ 
                video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } }, 
                audio: false 
            })
            .then(stream => { video.srcObject = stream; setInterval(captureAndAnalyze, 750); }) 
            .catch(err => { guidanceBox.innerText = "相機啟動失敗"; });

            function setManualZoom(factor) { autoZoomMode = false; updateZoomUI(factor); }

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
                                const decodedInstruction = decodeURIComponent(escape(raw));
                                guidanceBox.innerText = decodedInstruction;
                                arrowLeft.classList.remove('active');
                                arrowRight.classList.remove('active');
                                if (action === "left") arrowLeft.classList.add('active');
                                else if (action === "right") arrowRight.classList.add('active');
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
                    }, 'image/jpeg', 1.0);
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# =====================================================================
# ⚙️ 【即時分析 API 接口】🔥 整合美學與 Horizon 幾何引導
# =====================================================================
@app.post("/analyze-composition")
async def analyze_composition(file: UploadFile = File(...)):
    import cv2
    contents = await file.read()
    
    instructions = "構圖良好，請保持穩定"
    action_type = "hold"
    
    if model is not None:
        try:
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            results = model(img, verbose=False)
            
            best_box = None
            max_conf = 0
            for box in results[0].boxes:
                # 💡 Roboflow 訓練完的第一個標籤通常是 ID 0
                if int(box.cls[0]) == 0 and box.conf[0] > max_conf:
                    max_conf = box.conf[0]
                    best_box = box.xyxy[0].tolist()
            
            if best_box is not None:
                x1, y1, x2, y2 = best_box
                angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                
                # 判定手機是否傾斜
                if angle > 2.0:
                    instructions = f"⚠️ 畫面右傾 ({abs(angle):.1f}°)，請將手機逆時針稍作旋轉"
                    action_type = "left"
                elif angle < -2.0:
                    instructions = f"⚠️ 畫面左傾 ({abs(angle):.1f}°)，請將手機順時針稍作旋轉"
                    action_type = "right"
        except Exception as e:
            print(f"Horizon 幾何計算錯誤: {e}")

    output_buffer, eng_ins, eng_act = engine.analyze(contents)
    
    if action_type == "hold" and eng_ins:
        instructions = eng_ins
        action_type = eng_act
        
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
