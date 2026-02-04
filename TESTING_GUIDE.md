# ParallelDialer テスト手順書

最終更新: 2026-02-01

## 0. この手順書でできること
- **APIとWebSocketで動作確認**できる
- 自動発信が未接続でも、**擬似着信で雰囲気を確認**できる

## 1. まず知っておいてほしいこと（超重要）
- 画面（UI）はまだ仮なので、**APIとWebSocketで確認する**
- **自動で電話が発信される機能は未接続**
  - そのため「ボタンを押したら自動発信」は今は動かない
  - 代わりに WebSocket のテストイベントで着信を擬似体験できる

---

## 2. 前提（インストール済みのもの）
- Docker + Docker Compose
- Python 3.12+
- Node.js 20+

---

## 3. セットアップ（コピペOK）

### 3.1 DB/Redis を起動（ターミナル1）
```bash
cd /Users/akimare/FIXIM/ParallelCalling
docker-compose up -d
```

### 3.2 バックエンド起動（ターミナル2）
```bash
cd /Users/akimare/FIXIM/ParallelCalling/backend
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```
※ ローカルのポートがよく変わる場合は、`.env` の `CORS_ORIGIN_REGEX` を使うと便利。
起動できたら `http://localhost:8000/health` にアクセスして `{"status":"healthy"}` が返ればOK。

### 3.3 フロントエンド起動（任意 / 画面の雰囲気確認）
```bash
cd /Users/akimare/FIXIM/ParallelCalling/frontend
npm ci
cp .env.example .env
npm run dev
```
起動できたら `http://localhost:5173` にアクセス。
※ 画面はまだ仮のため、ここでは「起動できたか」だけ確認。

---

## 4. APIでの動作確認（実運用に近い流れ）

### 4.1 ログインしてトークン取得
```bash
curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

返ってきたJSONの `access_token` を控える。
以降のコマンドでは `Authorization: Bearer $TOKEN` を使う。

**便利なやり方（任意）**: トークンを環境変数に入れると楽。
```bash
TOKEN="<ここにaccess_tokenを貼り付け>"
```
※ もし環境変数を使わない場合は、`$TOKEN` の部分を実際の値に置き換える。

### 4.2 キャンペーン作成
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Demo Campaign",
    "description": "for test",
    "dial_ratio": 3.0,
    "caller_id": null
  }'
```

レスポンスの `id` を控える（以降 `$CAMPAIGN_ID` として使う）。

**便利なやり方（任意）**: キャンペーンIDも環境変数に入れる。
```bash
CAMPAIGN_ID="<ここにidを貼り付け>"
```
※ もし環境変数を使わない場合は、`$CAMPAIGN_ID` の部分を実際の値に置き換える。

### 4.3 リード追加（1件追加）
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/leads" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+14155551212",
    "name": "Test Lead",
    "company": "ACME",
    "email": "test@example.com",
    "notes": "demo"
  }'
```

### 4.4 CSVインポート（まとめて追加）
CSV例（必須列: `phone_number`）:
```csv
phone_number,name,company,email,notes
+14155550101,Lead A,Example Inc,lead-a@example.com,first
+14155550102,Lead B,Example Inc,lead-b@example.com,second
```

インポート実行:
```bash
curl -X POST "http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/leads/import" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/leads.csv"
```

### 4.5 キャンペーン操作（状態の切り替え）
```bash
# 開始
curl -X POST "http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/start" \
  -H "Authorization: Bearer $TOKEN"

# 一時停止
curl -X POST "http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/pause" \
  -H "Authorization: Bearer $TOKEN"

# 再開
curl -X POST "http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/resume" \
  -H "Authorization: Bearer $TOKEN"

# 停止
curl -X POST "http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/stop" \
  -H "Authorization: Bearer $TOKEN"
```

### 4.6 統計取得（数字が見えるか確認）
```bash
curl -X GET "http://localhost:8000/api/v1/campaigns/$CAMPAIGN_ID/stats" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 5. WebSocketでの動作確認（擬似着信）

### 5.1 準備
- WebSocketはトークン必須
- URLは次の2つ（`<TOKEN>` を実際の値に置き換える）
  - `ws://localhost:8000/ws/operator?token=<TOKEN>`
  - `ws://localhost:8000/ws/dashboard?token=<TOKEN>`

### 5.2 例: ブラウザコンソールでテスト
ブラウザの開発者ツール(Console)で実行:
`<TOKEN>` と `<CAMPAIGN_ID>` は実際の値に置き換える。

```js
const operatorWs = new WebSocket("ws://localhost:8000/ws/operator?token=<TOKEN>");
operatorWs.onmessage = (e) => console.log("operator", e.data);
operatorWs.onopen = () => {
  operatorWs.send(JSON.stringify({ action: "set_status", status: "available" }));
  operatorWs.send(JSON.stringify({
    action: "test_incoming_call",
    call_sid: "CA_TEST_001",
    lead_id: "lead-001",
    phone_number: "+14155551212",
    name: "Test Lead"
  }));
};

const dashboardWs = new WebSocket("ws://localhost:8000/ws/dashboard?token=<TOKEN>");
dashboardWs.onmessage = (e) => console.log("dashboard", e.data);
dashboardWs.onopen = () => {
  dashboardWs.send(JSON.stringify({ action: "get_operators" }));
  dashboardWs.send(JSON.stringify({ action: "subscribe_campaign", campaign_id: "<CAMPAIGN_ID>" }));
};
```

### 5.3 WebSocketの確認ポイント
- `operator_list_updated` がダッシュボード側に届く
- `incoming_call` がオペレーター側に届く
- `call_connected` / `call_ended` が想定通り返る

---

## 6. 「発信っぽい」テストのやり方（暫定）
**今は自動発信が未接続なので、以下のどちらかで代用する。**

### 6.1 WebSocketで擬似着信（おすすめ）
セクション5の `test_incoming_call` を使う。
オペレーター画面側に着信イベントが来ればOK。

### 6.2 Twilioの番号に「自分から電話」してWebhook確認
Twilio番号に自分の携帯から電話する。
バックエンドのログに `Voice webhook` が出ればOK。

---

## 7. Twilio連携の動作確認（任意 / 上級者向け）

### 7.1 前提
- 公開URL（ngrok等）が必要
- Twilioの設定が必要
- **自動発信は未実装**なので、ここでは「Webhookが呼ばれるか」を確認する

### 7.2 手順
1) ngrok を起動
```bash
ngrok http 8000
```

2) `backend/.env` に設定
```
PUBLIC_BASE_URL=https://xxxx.ngrok-free.app
TWILIO_USE_MOCK=false
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
TWILIO_API_KEY_SID=...
TWILIO_API_KEY_SECRET=...
TWILIO_APP_SID=...
TWILIO_VALIDATE_SIGNATURE=true
```

3) Twilio ConsoleでWebhook URLを設定
- Voice URL: `https://<PUBLIC_BASE_URL>/webhooks/twilio/voice`
- Status URL: `https://<PUBLIC_BASE_URL>/webhooks/twilio/status`
- AMD URL: `https://<PUBLIC_BASE_URL>/webhooks/twilio/amd`

4) Twilio番号へ着信して、Webhooksの受信ログを確認

---

## 8. 既知の制限（2026-02-01時点）
- 自動発信オーケストレーションが未接続
- UIが未実装（API/WSでの確認が中心）
- オペレーター割当の永続化が未実装
- 録音管理が未実装

---

## 9. つまずきやすいポイント
- `phone_number` は必ず E.164 形式（例: `+14155551212`）
- WebSocketは `token` がないと 4001 で切断される
- `PUBLIC_BASE_URL` が未設定だと Twilio署名検証が失敗する

---

必要なら、この手順書に「実発信の暫定的な起動方法」や
「UIができた後の操作フロー」を追記できる。
