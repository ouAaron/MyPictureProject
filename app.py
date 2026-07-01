# app.py
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
import io
from PIL import Image, ImageStat

app = FastAPI(title="PhotoFramer Academic Real-time App")

# 🎬 前端網頁：專業相機介面、嚴謹提示、拍完照「自動觸發儲存」
@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PhotoFramer AI 構圖美學引導系統</title>
        <style>
            body { margin: 0; background-color: #121212; font-family: -apple-system, sans-serif; overflow: hidden; display: flex; flex-direction: column; align-items: center; height: 100vh; color: white; }
            #camera-container { position: relative; width: 100%; max-width: 450px; height: 65vh; background: #000; overflow: hidden; border-radius: 16px; margin-top: 10px; box-shadow: 0 8px 24px rgba(0,0,0,0.6); }
            video { width: 100%; height: 100%; object-fit: cover; }
            
            /* 專業導演引導字幕框（無表情符號，強化學術感） */
            #guidance-box { position: absolute; top: 15px; left: 5%; width: 90%; background: rgba(0, 0, 0, 0.85); color: #00ffcc; padding: 12px 8px; border-radius: 10px; text-align: center; font-size: 15px; font-weight: bold; border: 1px solid #00ffcc; z-index: 10; box-shadow: 0 4px 12px rgba(0,0,0,0.5); letter-spacing: 0.5px; }
            
            /* 三分法輔助線 */
            .grid-line { position: absolute; background: rgba(255, 255, 255, 0.35); }
            .v1 { left: 33.33%; top: 0; width: 1.5px; height: 100%; } .v2 { left: 66.66%; top: 0; width: 1.5px; height: 100%; }
            .h1 { top: 33.33%; left: 0; height: 1.5px; width: 100%; } .h2 { top: 66.66%; left: 0; height: 1.5px; width: 100%; }
            
            /* 控制面板與快門鍵 */
            #control-panel { width: 100%; max-width: 450px; height: 25vh; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #121212; }
            #snap-btn { width: 76px; height: 76px; border-radius: 50%; background: white; border: 6px solid #333; cursor: pointer; box-shadow: 0 4px 10px rgba(0,0,0,0.4); transition: all 0.2s; }
            #snap-btn:active { transform: scale(0.9); background: #ff3b30; }
            #status { color: #8e8e93; font-size: 13px; margin-bottom: 15px; text-align: center; }

            /* 拍照成功提示彈窗 */
            #result-modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 100; flex-direction: column; align-items: center; justify-content: center; }
            #result-img { max-width: 90%; max-height: 65vh; border-radius: 12px; border: 2px solid #fff; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
            #modal-close-btn { margin-top: 25px; padding: 12px 30px; background: #007aff; color: white; border: none; border-radius: 25px; font-size: 16px; font-weight: bold; cursor: pointer; }
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
            <div id="status">大腦連線狀態：連線中</div>
            <button id="snap-btn"></button>
        </div>

        <div id="result-modal">
            <h3 style="color: #00ffcc; margin-bottom: 5px;">構圖優化完成</h3>
            <p style="color: #aaa; font-size: 13px; margin-bottom: 15px;">照片已自動儲存至您的裝置</p>
            <img id="result-img" src="" alt="AI Optimized Image">
            <button id="modal-close-btn" onclick="closeModal()">返回拍攝</button>
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

            navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
            .then(stream => {
                video.srcObject = stream;
                statusText.innerText = "系統狀態：美學引導中";
                setInterval(captureAndAnalyze, 1200);
            })
            .catch(err => {
                guidanceBox.innerText = "錯誤：相機啟動失敗，請確認權限";
            });

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
                                guidanceBox.innerText = decoded.split('|')[0].trim();
                            }
                        })
                        .catch(err => { console.error(err); });
                    }, 'image/jpeg', 0.4);
                }
            }

            // 📸 核心變更：拍照按鈕觸發後，自動下載（儲存）照片到相簿/裝置
            snapBtn.addEventListener('click', () => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    statusText.innerText = "正在儲存並優化構圖中...";
                    
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    canvas.toBlob((blob) => {
                        if (!blob) return;
                        const formData = new FormData();
                        formData.append('file', blob, 'capture.jpg');

                        fetch(API_URL, { method: 'POST', body: formData })
                        .then(response => response.blob())
                        .then(imageBlob => {
                            const blobUrl = URL.createObjectURL(imageBlob);
                            resultImg.src = blobUrl;
                            
                            // 🔥 【學術標準：自動觸發裝置下載儲存行為】
                            const downloadLink = document.createElement('a');
                            downloadLink.href = blobUrl;
                            downloadLink.download = `PhotoFramer_${Date.now()}.jpg`; // 自動產生不重複的檔名
                            document.body.appendChild(downloadLink);
                            downloadLink.click(); // 模擬點擊，強制手機自動下載保存照片
                            document.body.removeChild(downloadLink);

                            resultModal.style.display = 'flex';
                            statusText.innerText = "系統狀態：美學引導中";
                        })
                        .catch(err => {
                            alert("拍攝失敗: " + err);
                        });
                    }, 'image/jpeg', 0.95); // 提高儲存相片的高畫質品質
                }
            });

            function closeModal() {
                resultModal.style.display = 'none';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

# 🧠 後端大腦：拉高美學判定標準（降低容忍度，讓判定更精準嚴格）
@app.post("/analyze-composition")
async def analyze_composition(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        orig_img = Image.open(io.BytesIO(contents))
        orig_img = orig_img.convert("RGB")
    except:
        return JSONResponse(status_code=400, content={"message": "無效的圖片格式"})
    
    w, h = orig_img.size
    
    # 三分法區域精細切割
    left_third = orig_img.crop((0, 0, w // 3, h))
    right_third = orig_img.crop(((2 * w) // 3, 0, w, h))
    center_core = orig_img.crop((w // 4, h // 4, (3 * w) // 4, (3 * h) // 4))
    
    # 統計特徵密度
    stat_left = ImageStat.Stat(left_third).rms[0]
    stat_right = ImageStat.Stat(right_third).rms[0]
    stat_center = ImageStat.Stat(center_core).rms[0]
    stat_global = ImageStat.Stat(orig_img).rms[0]
    
    instructions = []
    
    # 🔥 【嚴格調校點】：將判定的不平衡係數從原本的 1.15 倍，縮緊至更靈敏的 1.05 倍
    # 這樣一來，只要畫面主體稍微偏離，系統就會果斷給予物理校正方向
    imbalance_threshold = 1.05 
    
    # 左右軸向（水平位置）精確判定
    if stat_left > stat_right * imbalance_threshold:
        instructions.append("[請向左平移移鏡頭] 修正當前主體偏右情形，使視覺特徵靠向黃金分割線線位置")
    elif stat_right > stat_left * imbalance_threshold:
        instructions.append("[請向右平移移鏡頭] 修正當前主體偏左情形，使視覺特徵靠向黃金分割線線位置")
    else:
        # 當左右平衡時，切換至深度（Z軸）或構圖完成判定
        # 這裡我們保留這兩段框架，等一下直接來攻克放大縮小的極端問題！
        if stat_center < stat_global * 0.9:
            instructions.append("[建議前進或放大焦距] 核心特徵占比過低，建議縮減環境冗餘邊緣")
        elif stat_center > stat_global * 1.15:
            instructions.append("[建議後退或縮小焦距] 視覺主體壓迫感過強，建議保留畫面呼吸空間")
        else:
            instructions.append("構圖指標已達美學標準，可直接按下拍攝鈕")

    # 推薦裁剪幾何位置定位
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
