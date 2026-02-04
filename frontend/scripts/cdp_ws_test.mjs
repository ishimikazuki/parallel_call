import { chromium } from "playwright";

const CDP_URL = process.env.CDP_URL || "http://127.0.0.1:9222";
const APP_URL = process.env.APP_URL || "http://localhost:5173/";
const API_BASE = process.env.API_BASE || "http://127.0.0.1:8000";
const WAIT_MS = Number(process.env.WAIT_MS || 6000);

async function run() {
  const browser = await chromium.connectOverCDP(CDP_URL);
  const context = browser.contexts()[0] ?? (await browser.newContext());
  const page = context.pages()[0] ?? (await context.newPage());

  page.on("console", (msg) => {
    const prefix = msg.type().toUpperCase();
    console.log(`PAGE_${prefix}:`, msg.text());
  });
  page.on("pageerror", (err) => {
    console.error("PAGE_ERROR:", err?.message ?? String(err));
  });

  await page.goto(APP_URL, { waitUntil: "domcontentloaded" });

  const result = await page.evaluate(async ({ apiBase }) => {
    try {
      const loginRes = await fetch(`${apiBase}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "username=admin&password=admin123",
      });
      const loginData = await loginRes.json();
      const token = loginData.access_token;
      if (!token) {
        return { ok: false, error: "login failed", data: loginData };
      }

      const campRes = await fetch(`${apiBase}/api/v1/campaigns`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: "WS Test Campaign",
          description: "websocket test",
          dial_ratio: 3.0,
          caller_id: null,
        }),
      });
      const camp = await campRes.json();
      const campaignId = camp.id;
      if (!campaignId) {
        return { ok: false, error: "campaign create failed", data: camp };
      }

      const wsBase = apiBase.replace(/^http/, "ws");
      const operatorWs = new WebSocket(`${wsBase}/ws/operator?token=${token}`);
      operatorWs.onmessage = (e) => console.log("operator", e.data);
      operatorWs.onopen = () => {
        operatorWs.send(JSON.stringify({ action: "set_status", status: "available" }));
        operatorWs.send(
          JSON.stringify({
            action: "test_incoming_call",
            call_sid: "CA_TEST_001",
            lead_id: "lead-001",
            phone_number: "+14155551212",
            name: "Test Lead",
          })
        );
      };

      const dashboardWs = new WebSocket(`${wsBase}/ws/dashboard?token=${token}`);
      dashboardWs.onmessage = (e) => console.log("dashboard", e.data);
      dashboardWs.onopen = () => {
        dashboardWs.send(JSON.stringify({ action: "get_operators" }));
        dashboardWs.send(
          JSON.stringify({ action: "subscribe_campaign", campaign_id: campaignId })
        );
      };

      return { ok: true, token, campaignId, wsBase };
    } catch (err) {
      return { ok: false, error: String(err) };
    }
  }, { apiBase: API_BASE });

  console.log("RESULT:", JSON.stringify(result));

  await new Promise((resolve) => setTimeout(resolve, WAIT_MS));
  await browser.close();
}

run().catch((err) => {
  console.error("FATAL:", err);
  process.exit(1);
});
