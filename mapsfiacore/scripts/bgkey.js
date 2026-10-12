#!/usr/bin/env node
/**
 * x-maps-bgkey generator for Google Maps Batchexecute (MapsWizUi).
 *
 * Fully reverse-engineered from maps.m.*.js and the BotGuard interpreter.
 *
 * CHAIN (identical to the browser):
 *   f.req -> Ggb extracts the RPC payload string
 *         -> Waa/Create  ["N6KF9UNi6tEjCToKNPTx"]
 *              response field[1] = base64(byte blob shifted +97)
 *              decoded = ["bfkj",null,[null,null,null,"//www.google.com/js/bg/<ID>.js"],"<ID>","<ENC>"]
 *         -> load //www.google.com/js/bg/<ID>.js  -> window.botguard.a
 *         -> botguard.a(ENC, h, true, undefined, g, [[],[]], false, false, l)
 *              h(ICb, kRb, u0e, mYe)  where ICb is a function
 *         -> ICb(cb, [requestData, ...])  -> cb(key)   <-- x-maps-bgkey
 *
 * Usage:
 *   node bgkey.js '<requestData>'      print key to stdout
 *
 * Or import:  const { getXmapsBgkey } = require('./bgkey.js')
 */

"use strict";
const vm = require("vm");
const crypto = require("crypto");

const WAA_HOST = "https://waa-pa.clients6.google.com";

// Defaults (verified). If Google rotates these, run discover_waa.js or set
// env WAA_API_KEY / WAA_PROGRAM_ID. getXmapsBgkey() will also auto-discover
// once on failure.
let WAA_API_KEY = process.env.WAA_API_KEY || "AIzaSyBGb5fGAyC-pRcRU6MUHb__b_vKha71HRE";
let PROGRAM_ID = process.env.WAA_PROGRAM_ID || "N6KF9UNi6tEjCToKNPTx";
const UA =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36";

// --------------------------------------------------------------------------
// Waa transport
// --------------------------------------------------------------------------

function b64ShiftedToJson(field) {
  const raw = Buffer.from(field, "base64");
  const dec = Buffer.alloc(raw.length);
  for (let i = 0; i < raw.length; i++) dec[i] = (raw[i] + 97) & 0xff;
  return JSON.parse(dec.toString("utf8"));
}

async function waa(method, body) {
  const res = await fetch(`${WAA_HOST}/$rpc/google.internal.waa.v1.Waa/${method}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json+protobuf",
      "X-User-Agent": "grpc-web-javascript/0.1",
      "X-Goog-Api-Key": WAA_API_KEY,
      Origin: "https://www.google.com",
      Referer: "https://www.google.com/",
      "User-Agent": UA,
    },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`Waa/${method} HTTP ${res.status}: ${text}`);
  return JSON.parse(text);
}

/** Step 1: obtain BotGuard program + interpreter URL. */
async function createChallenge() {
  const resp = await waa("Create", [PROGRAM_ID]);
  if (resp[0] != null) throw new Error("Create error: " + JSON.stringify(resp[0]));
  const decoded = b64ShiftedToJson(resp[1]);
  const [, , meta, programId, payload] = decoded;
  const interpreterUrl = meta && meta[3] ? meta[3] : null;
  if (!interpreterUrl) throw new Error("no interpreter url in Create response");
  return { programId, payload, interpreterUrl };
}

// --------------------------------------------------------------------------
// BotGuard interpreter sandbox
// --------------------------------------------------------------------------

function el() {
  return {
    setAttribute() {}, getAttribute() { return null; }, appendChild() {},
    removeChild() {}, style: {}, addEventListener() {}, removeEventListener() {},
    getContext() { return {}; }, innerHTML: "", children: [],
  };
}

function makeSandbox() {
  const sb = {};
  sb.window = sb; sb.self = sb; sb.globalThis = sb; sb.top = sb;
  sb.navigator = {
    userAgent: UA, webdriver: false, languages: ["en-US"],
    platform: "Linux", hardwareConcurrency: 8, deviceMemory: 8,
  };
  sb.document = {
    createElement: el, documentElement: el(), body: el(), head: el(),
    location: { href: "https://www.google.com/maps" }, cookie: "",
    addEventListener() {}, querySelector() { return null; },
    querySelectorAll() { return []; }, getElementsByTagName() { return []; },
  };
  sb.location = { href: "https://www.google.com/maps", protocol: "https:" };
  for (const k of ["setTimeout", "clearTimeout", "setInterval", "clearInterval"])
    sb[k] = global[k];
  Object.assign(sb, {
    console, Date, Math, JSON,
    Uint8Array, Int8Array, Uint16Array, Int32Array,
    Float32Array, Float64Array, ArrayBuffer, DataView, TextDecoder, TextEncoder,
    btoa: (s) => Buffer.from(s, "binary").toString("base64"),
    atob: (s) => Buffer.from(s, "base64").toString("binary"),
    crypto: crypto.webcrypto,
    performance: { now: () => Date.now() },
    screen: { width: 1920, height: 1080, colorDepth: 24 },
    addEventListener() {}, removeEventListener() {}, fetch,
  });
  return sb;
}

let cachedInterpreter = null;

async function loadBotguard(interpreterUrl) {
  if (cachedInterpreter) return cachedInterpreter;
  const url = interpreterUrl.startsWith("//") ? "https:" + interpreterUrl : interpreterUrl;
  const js = await (await fetch(url, { headers: { "User-Agent": UA } })).text();
  const sb = makeSandbox();
  const ctx = vm.createContext(sb);
  vm.runInContext(js, ctx, { filename: "botguard.js", timeout: 15000 });
  if (!sb.botguard || typeof sb.botguard.a !== "function")
    throw new Error("BotGuard interpreter did not export botguard.a");
  cachedInterpreter = sb.botguard;
  return cachedInterpreter;
}

// --------------------------------------------------------------------------
// Public API
// --------------------------------------------------------------------------

/**
 * Generate a fresh x-maps-bgkey bound to `requestData`.
 * @param {string} requestData - the RPC payload string extracted from f.req (Ggb).
 * @returns {Promise<string>}
 */
async function getXmapsBgkey(requestData = "") {
  const { payload, interpreterUrl } = await createChallenge();
  const bg = await loadBotguard(interpreterUrl);

  const key = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => resolve(null), 15000);
    // h(ICb, kRb, u0e, mYe): ICb is the VM function we invoke.
    const h = (ICb) => {
      try {
        // Kab.Km passes [a.xVa(=request), a.F1e, a.u2e, a.G1e]
        ICb(
          (f) => { clearTimeout(timer); resolve(f); },
          [requestData, undefined, undefined, undefined]
        );
      } catch (e) { clearTimeout(timer); reject(e); }
    };
    const g = () => {};                             // status callback
    const l = [() => {}, () => {}, () => {}, () => {}]; // he.H/nm/va/ha stubs
    bg.a(payload, h, true, undefined, g, [[], []], false, false, l);
  });

  if (!key) throw new Error("BotGuard did not return a key (timeout)");
  if (typeof key !== "string" || !key.startsWith("!"))
    throw new Error(`BotGuard returned non-key value: ${String(key).slice(0, 120)}`);
  return key;
}

// --------------------------------------------------------------------------
// High-level helper: build the MapsWizUi (qv9Egd) request from place fields
// --------------------------------------------------------------------------

/**
 * Build the qv9Egd RPC payload string (the object Ggb extracts from f.req).
 *
 * Layout (verified against the live RPC):
 *   [0][0][0]  fid          "0x...:0x..."   (feature id)
 *   [1]        [10, token]  the query/session token ("...:NN")
 *   [4][0]     place_id     "It7CatX8..."   (the /m/ or encoded place id)
 *
 * @param {string} fid           e.g. "0x2e7a15ca78f42c63:0xdc8077d4d6be4249"
 * @param {string} placeId       e.g. "It7CatX8G7qd4-EPj_fXyQE"
 * @param {string} [paginationToken] token returned as d[0][2][1] from a prior
 *                                   qv9Egd response, to fetch the next page.
 *                                   Pass "" (or omit) for the first page.
 * @returns {string} JSON payload string
 */
function buildQv9EgdPayload(fid, placeId, paginationToken = "") {
  if (!fid) throw new Error("fid is required");
  if (!placeId) throw new Error("placeId is required");
  const payload = [
    [[fid], null, null, null, null, [null, null, null, [[1], [3]]]],
    [10, paginationToken || ""],
    null,
    null,
    [placeId, null, null, null, null, null, 81],
    null,
    null,
    [null, 1, 1, null, 1, null, 1, null, null, null, null, [1, 1, null, [[1]]]],
    null,
    null,
    [3, 1, null, null, null, [2]],
    null,
    [1],
  ];
  return JSON.stringify(payload);
}

/**
 * Convenience: generate x-maps-bgkey directly from fid + place_id
 * (+ optional pagination token).
 *
 * @param {string} fid
 * @param {string} placeId
 * @param {string} [paginationToken]
 * @returns {Promise<string>} the x-maps-bgkey value
 */
async function getBgkeyForPlace(fid, placeId, paginationToken = "") {
  const requestData = buildQv9EgdPayload(fid, placeId, paginationToken);
  return getXmapsBgkey(requestData);
}

module.exports = {
  getXmapsBgkey,
  getBgkeyForPlace,
  buildQv9EgdPayload,
  createChallenge,
};

// --------------------------------------------------------------------------
// Auto-discovery fallback (if Google rotates PROGRAM_ID / WAA_API_KEY)
// --------------------------------------------------------------------------

async function autorefreshConstants() {
  try {
    const { execFileSync } = require("child_process");
    const out = execFileSync("node", [__dirname + "/discover_waa.js"], { encoding: "utf8" });
    const pid = out.match(/PROGRAM_ID\s*:\s*(\S+)/);
    const key = out.match(/WAA_API_KEY\s*:\s*(\S+)/);
    let changed = false;
    if (pid && pid[1] && pid[1] !== PROGRAM_ID) { PROGRAM_ID = pid[1]; changed = true; }
    if (key && key[1] && key[1] !== WAA_API_KEY) { WAA_API_KEY = key[1]; changed = true; }
    return changed;
  } catch {
    return false;
  }
}

// --------------------------------------------------------------------------
// Line protocol ("server" mode) for Python/other-language pipelines.
//   node bgkey.js --stdio
// Reads one JSON request per line on stdin, writes one JSON response per line:
//   {"fid":"0x..:0x..","placeId":"It7..","pagination":".."}  -> {"key":"!..."}
//   {"requestData":"<raw>"}                                   -> {"key":"!..."}
//   {"cmd":"ping"}                                            -> {"ok":true}
// --------------------------------------------------------------------------
async function stdioServer() {
  const readline = require("readline");
  const rl = readline.createInterface({ input: process.stdin });

  const isBadKey = (k) => !k || typeof k !== "string" || !k.startsWith("!");

  const generateOnce = async (req) => {
    if (req.fid && req.placeId) return getBgkeyForPlace(req.fid, req.placeId, req.pagination || "");
    return getXmapsBgkey(req.requestData || "");
  };

  const handle = async (reqLine) => {
    let req;
    try { req = JSON.parse(reqLine); } catch { return { error: "invalid json" }; }
    try {
      if (req.cmd === "ping") return { ok: true };
      // Retry on transient VM errors (occasionally the first run in a fresh
      // context yields "E:..." instead of a key).
      let lastErr = "unknown";
      for (let attempt = 1; attempt <= 3; attempt++) {
        const key = await generateOnce(req);
        if (!isBadKey(key)) return { key };
        lastErr = key;
        await new Promise((r) => setTimeout(r, 50 * attempt));
      }
      return { error: `bad key after retries: ${lastErr}` };
    } catch (e) {
      return { error: String(e.message || e) };
    }
  };

  // Serialize handling: only one request in flight at a time.
  let chain = Promise.resolve();
  rl.on("line", (line) => {
    if (!line.trim()) return;
    chain = chain.then(async () => {
      const res = await handle(line.trim());
      process.stdout.write(JSON.stringify(res) + "\n");
    });
  });
}

if (require.main === module) {
  (async () => {
    // CLI modes:
    //   node bgkey.js --stdio                                    (line protocol)
    //   node bgkey.js --gen <fid> <place_id> [pagination_token]
    //   node bgkey.js '<raw requestData>'
    const argv = process.argv.slice(2);
    if (argv[0] === "--stdio") { await stdioServer(); return; }
    const isPlace = argv[0] === "--gen";

    const run = async () => {
      if (isPlace) {
        const [, fid, placeId, pageToken = ""] = argv;
        if (!fid || !placeId) {
          console.error("usage: node bgkey.js --gen <fid> <place_id> [pagination_token]");
          process.exit(2);
        }
        return getBgkeyForPlace(fid, placeId, pageToken);
      }
      return getXmapsBgkey(argv[0] || "");
    };

    try {
      console.log(await run());
    } catch (e) {
      console.error("first attempt failed:", e.message);
      console.error("→ trying to auto-discover new PROGRAM_ID / WAA_API_KEY ...");
      if (await autorefreshConstants()) {
        console.error(`  updated: PROGRAM_ID=${PROGRAM_ID} WAA_API_KEY=${WAA_API_KEY}`);
        console.log(await run());
      } else {
        console.error("no new constants found; run discover_waa.js manually");
        process.exit(1);
      }
    }
  })();
}
