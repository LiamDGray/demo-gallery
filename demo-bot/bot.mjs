#!/usr/bin/env node
/**
 * Demo Approval Bot — Telegram bot for the demo.liamdgray.com approval flow.
 *
 * When a visitor requests access to a demo, the bot sends you an inline
 * keyboard message. Tap [Approve] → token is issued. Tap [Deny] → visitor
 * is told no.
 *
 * Usage:
 *   export TG_BOT_TOKEN="..."
 *   export TG_CHAT_ID="123456789"      # Your Telegram user/group chat ID
 *   node bot.mjs
 *
 * If TG_CHAT_ID is empty, the bot prints a URL on first message to let you
 * discover your chat ID.
 */

const BOT_TOKEN = process.env.DEMO_APPROVAL_BOT_TOKEN || "";
const CHAT_ID = process.env.DEMO_APPROVAL_CHAT_ID || "";
const AUTH_URL = process.env.AUTH_URL || "http://127.0.0.1:8090";
const POLL_INTERVAL = parseInt(process.env.POLL_INTERVAL || "3000", 10);
const ADMIN_KEY = process.env.DEMO_APPROVAL_ADMIN_KEY || "";

if (!BOT_TOKEN) {
  console.error("FATAL: DEMO_APPROVAL_BOT_TOKEN is required");
  process.exit(1);
}

const TG_API = `https://api.telegram.org/bot${BOT_TOKEN}`;

// ── Telegram helpers ───────────────────────────────────────────────────────

async function tg(method, body = {}) {
  const res = await fetch(`${TG_API}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!data.ok) {
    console.error(`[TG ERROR] ${method}:`, data.description);
  }
  return data;
}

async function sendApprovalMessage(req) {
  const demo_emoji = {
    "geo-csg": "🏗️",
    "voice-chat": "🎤",
    "agent-debate": "⚖️",
    "name-check": "🔍",
    "realpeep": "👁️",
    "afterlife": "💀",
    "artcall": "🎨",
  };
  const emoji = demo_emoji[req.demo_id] || "🔘";

  const text = [
    `🔔 New Demo Request`,
    ``,
    `${emoji} Demo: **${req.demo_id}**`,
    `🌐 IP: \`${req.visitor_ip}\``,
    req.email ? `📧 Email: \`${req.email}\`` : "",
    req.reason ? `💬 Reason: ${req.reason}` : "",
    `🕐 ${new Date(req.created_at * 1000).toISOString()}`,
    ``,
    `_Approve to issue a time-limited token. Deny to reject._`,
  ]
    .filter(Boolean)
    .join("\n");

  await tg("sendMessage", {
    chat_id: CHAT_ID,
    text,
    parse_mode: "Markdown",
    reply_markup: {
      inline_keyboard: [
        [
          { text: "✅ Approve (24h)", callback_data: `approve:${req.id}:24` },
          { text: "✅ Approve (72h)", callback_data: `approve:${req.id}:72` },
          { text: "✅ Approve (7d)", callback_data: `approve:${req.id}:168` },
        ],
        [
          { text: "❌ Deny", callback_data: `deny:${req.id}` },
        ],
      ],
    },
  });
}

async function handleCallback(cb) {
  const [action, rid, hours] = cb.data.split(":");

  if (action === "approve") {
    const duration = parseInt(hours) || 24;
    const res = await fetch(`${AUTH_URL}/api/resolve/${rid}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Key": ADMIN_KEY,
      },
      body: JSON.stringify({ action: "approve", duration_hours: duration, max_uses: 1 }),
    });

    if (!res.ok) {
      const err = await res.text();
      await tg("answerCallbackQuery", {
        callback_query_id: cb.id,
        text: `❌ Error: ${err.slice(0, 100)}`,
        show_alert: true,
      });
      return;
    }

    const result = await res.json();
    await tg("editMessageText", {
      chat_id: cb.message.chat.id,
      message_id: cb.message.message_id,
      text: cb.message.text + `\n\n✅ **Approved** (${duration}h)`,
      parse_mode: "Markdown",
      reply_markup: { inline_keyboard: [] },
    });

    await tg("sendMessage", {
      chat_id: cb.message.chat.id,
      text: `🔗 Token URL:\n\`${result.url}\``,
      parse_mode: "Markdown",
    });

    await tg("answerCallbackQuery", {
      callback_query_id: cb.id,
      text: `✅ Approved! Token issued for ${duration}h.`,
    });
  } else if (action === "deny") {
    await fetch(`${AUTH_URL}/api/resolve/${rid}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Key": ADMIN_KEY,
      },
      body: JSON.stringify({ action: "deny" }),
    });

    await tg("editMessageText", {
      chat_id: cb.message.chat.id,
      message_id: cb.message.message_id,
      text: cb.message.text + `\n\n❌ **Denied**`,
      parse_mode: "Markdown",
      reply_markup: { inline_keyboard: [] },
    });

    await tg("answerCallbackQuery", {
      callback_query_id: cb.id,
      text: "❌ Request denied.",
    });
  }
}

// ── Main loop ──────────────────────────────────────────────────────────────

let offset = 0;
let knownRequests = new Set();

async function pollLoop() {
  console.log(`[BOT] Starting poll loop (interval: ${POLL_INTERVAL}ms)`);

  // If no CHAT_ID, print discovery info every loop
  if (!CHAT_ID) {
    console.error("[BOT] DEMO_APPROVAL_CHAT_ID not set. Send a message to your bot, then check the console.");
  }

  while (true) {
    try {
      // 1. Process Telegram updates (callback queries, /start, etc.)
      if (BOT_TOKEN) {
        const res = await fetch(
          `${TG_API}/getUpdates?offset=${offset}&timeout=10&allowed_updates=["callback_query","message"]`
        );
        const data = await res.json();
        if (data.ok && data.result) {
          for (const update of data.result) {
            // Discover chat ID if not set
            if (!CHAT_ID && update.message?.chat?.id) {
              const cid = update.message.chat.id;
              console.log(`[BOT] 📬 Message from chat ID: ${cid}`);
              console.log(`[BOT] Set DEMO_APPROVAL_CHAT_ID=${cid} in sops/environment`);
              console.log(`[BOT] Message: ${update.message.text || "(no text)"}`);
              await tg("sendMessage", {
                chat_id: cid,
                text: `Hello! Your chat ID is \`${cid}\`.\nSet \`DEMO_APPROVAL_CHAT_ID=${cid}\` in the environment to receive demo approval requests.`,
                parse_mode: "Markdown",
              });
            }

            if (update.callback_query) {
              await handleCallback(update.callback_query);
            }

            offset = update.update_id + 1;
          }
        }
      }

      // 2. Poll auth service for pending requests
      if (CHAT_ID) {
        const res = await fetch(`${AUTH_URL}/api/pending`);
        if (res.ok) {
          const pending = await res.json();
          for (const req of pending) {
            if (!knownRequests.has(req.id)) {
              knownRequests.add(req.id);
              await sendApprovalMessage(req);
              console.log(`[BOT] New request: ${req.demo_id} from ${req.visitor_ip}`);
            }
          }
        }
      }
    } catch (e) {
      console.error(`[BOT] Error:`, e.message);
    }

    await new Promise(r => setTimeout(r, POLL_INTERVAL));
  }
}

pollLoop().catch(e => {
  console.error("[BOT] Fatal:", e);
  process.exit(1);
});
