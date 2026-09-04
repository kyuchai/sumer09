# Plantopia Final Edition

PC 端遊戲化植栽資產管理系統。此版本同時支援 **Windows + VS Code + Python 3.12 + SQLite** 本機開發，以及 **Render + PostgreSQL** 線上部署，不需要 Docker。

## 第一次執行（最簡單）

1. 解壓縮專案。
2. 雙擊 `SETUP_FIRST_TIME.bat`，它會建立 Python 3.12 `.venv`、安裝後端套件及執行 `npm.cmd install`。
3. 安裝完成後雙擊 `START_PLANTOPIA.bat`。
4. 瀏覽器開啟 `http://localhost:5173`。
5. API/Swagger：`http://127.0.0.1:8000/docs`。

## VS Code 手動執行

後端 Terminal：

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

前端另一個 Terminal：

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

之後不需要再次 `pip install` / `npm install`，只要啟動後端與 `npm.cmd run dev`。

## 最終版功能

- 植栽 CRUD、場域篩選、HP 與動態澆水 MP / Cooldown
- 出差緊急照顧排序
- 18 種鹿角蕨圖鑑進度（學名依 Kew Plants of the World Online 的 accepted species 清單整理）
- 母株 / 父本 / 側芽 Gene Tree 與雜交稀有標記
- 四角度 Photo Log：全景、葉正反面、莖基部、介質；本機 `backend/uploads` 歸檔
- 死亡墓碑、死因與損耗結算、死因圓餅圖
- 採收重量紀錄
- 固定資產 / 消耗品 RPG Inventory、20% 低庫存警報
- 換盆：新盆扣庫存、舊盆回存、介質扣量
- 分株：建立子株、母株綁定、盆器連動
- 售出淨利：`售價 - 購入成本 - 資產攤銷 - 分株成本`
- 賣家存活率與 CP Score 排行
- 財務總覽與月度現金流
- Compost Reactor C/N 教學型配比試算與濕度提醒
- 中央氣象署預報整合：露天無雨遮場域預期降雨時延後澆水 1 天

## 中央氣象署 API（選用）

沒有 API Key 時，**整套系統仍可正常使用**，氣象頁只會顯示未啟用。

若要啟用：

1. 複製 `backend/.env.example` 為 `backend/.env`。
2. 填入：

```env
CWA_API_KEY=你的授權碼
```

3. 場域的 `cwa_location` 請使用縣市名稱，例如 `臺中市`。

系統使用中央氣象署一般天氣預報資料集 `F-C0032-001` 的降雨機率 (PoP)；最高 PoP >= 50% 時，露天且無雨遮的場域澆水週期增加 1 天。API 失敗時採 fail-safe：維持原澆水週期，不阻斷操作。

## 資料庫與照片

預設 SQLite：`backend/plantopia.db`，第一次啟動會自動建立。照片存在 `backend/uploads/`。要重新開始測試可關閉後端後刪除 `plantopia.db`。

## 測試

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

本交付版核心自動測試涵蓋 health、買入/售出/淨利、分株/盆器庫存/Gene Tree、原生種進度、堆肥與緊急照顧。

## 主要演算法說明

- **Water MP**：依「距上次澆水天數 / 有效澆水週期」線性遞減至 0；露天場域若預期降雨，有效週期 +1 天。
- **Emergency Score**：`距上次澆水天數 / 耐旱天數`，由高至低排序。
- **Net Profit**：`售價 - 購入成本 - 攤銷成本 - 分株成本`。
- **Seller CP Score**：以存活率為主權重，再納入平均存活時間及平均購入成本，作為站內相對排行，不宣稱為市場標準指標。
- **Compost**：目前為教學型高碳/高氮材料重量配比指標；25–35 為系統提醒區間，另依濕度 <40%、>65% 產生操作提示。若要做農業研究用途，應再改成每種材料個別 C/N 與含水率的質量平衡模型。

## 注意

這是本機單機交付版，因此照片預設存在本機，不要求 S3；資料庫預設 SQLite，不要求 PostgreSQL。兩者都可在未來部署版替換，不影響目前課堂展示與核心驗收。

## Render 一鍵部署版

根目錄已包含 `render.yaml` 與 `Dockerfile`。**Docker 只由 Render 在雲端建置時使用，你在 Windows / VS Code 本機完全不需要安裝或操作 Docker。** Render 會自動完成 React build、FastAPI 安裝與啟動，並連接 PostgreSQL。

1. 將整個 `plantopia` 資料夾推到 GitHub，確認 `render.yaml` 與 `Dockerfile` 位於 repository 根目錄。
2. Render Dashboard → **New → Blueprint** → 選擇該 GitHub repository。
3. Render 會依 `render.yaml` 建立 `plantopia-final` Web Service 與 `plantopia-db` PostgreSQL。
4. 第一次建立 Blueprint 時會要求填入 `CWA_API_KEY`，把中央氣象署授權碼貼在 Render 的欄位中；不要把 Key 寫進 GitHub。
5. Deploy 成功後直接開 Render 提供的 `https://...onrender.com` 網址；Swagger 為同網址加 `/docs`。

Render 版採單一網域：FastAPI 同時提供 API 與 build 後的 React，因此不需要另外建立 Static Site，也不用設定正式環境的 `VITE_API_URL`。本機 `npm.cmd run dev` 仍會自動連 `http://localhost:8000`。

### Render 資料持久化

部署版會從 `DATABASE_URL` 自動切換到 Render PostgreSQL；本機沒有 `DATABASE_URL` 時仍使用 SQLite。照片的原始影像同時寫入資料庫 `photo_blobs`，因此不依賴 Render Web Service 的暫存檔案系統。

> Render 官方目前說明 Free Postgres 適合測試/展示，但免費資料庫會在建立 **30 天後到期**，且沒有備份。課堂展示可以使用；若要長期對外使用，請升級資料庫或改接其他持久化 PostgreSQL。

### 之後修改程式

平常仍照原本 VS Code 方式開發：

```powershell
# Backend
cd backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload

# Frontend（另一個 Terminal）
cd frontend
npm.cmd run dev
```

修改完成後只要 commit / push GitHub，Render 會重新建置 Docker image，**不需要你自己執行 Docker，也不需要先把 frontend build 出來。**
