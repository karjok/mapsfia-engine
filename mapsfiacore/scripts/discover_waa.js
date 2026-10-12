#!/usr/bin/env node
/**
 * Discover the CURRENT WAA PROGRAM_ID and X-Goog-Api-Key used by Google Maps
 * to compute x-maps-bgkey, whenever Google rotates them.
 *
 * Strategy (fully automatic):
 *   1. Fetch https://www.google.com/maps/ and extract the module bootstrap.
 *   2. Build bundle URLs that ask Google for the full module set.
 *   3. Scan each bundle for the two constants at the same code sites used by
 *      the bgkey chain:
 *        PROGRAM_ID  ->  _.vg(a,1,"<ID>") / _.w(b,1,"<ID>") / .U("c","<ID>",..)
 *        WAA_API_KEY ->  {"X-Goog-Api-Key":"AIza..."} next to waa-pa host
 *
 * Usage:
 *   node discover_waa.js                 # auto (homepage + full module set)
 *   node discover_waa.js <bundle-url>... # scan explicit URLs
 *
 * Output: paste-ready constants for bgkey.js.
 */

"use strict";
const UA =
  "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36";
const BASE = "https://www.google.com";

async function get(url) {
  const res = await fetch(url, { headers: { "User-Agent": UA } });
  if (!res.ok) throw new Error(`GET ${url} -> HTTP ${res.status}`);
  return res.text();
}

/** Pull the loader config (k, ck, am, rs, modules) from the maps homepage. */
async function bootstrap() {
  const html = await get(BASE + "/maps/");
  // primary loader line: /maps/_/js/k=.../ck=.../am=.../rt=j/d=1/rs=.../m=<modules>
  const m =
    html.match(/\/maps\/_\/js\/k=([^/]+)\/ck=([^/]+)\/am=([^/]+)\/rt=j\/d=1\/rs=([^?"']+)/) ||
    html.match(/\/maps\/_\/js\/k=([^/]+)[^"']*?rs=([^?"']+)/);
  const modules = [...html.matchAll(/\/m=([A-Za-z0-9_$\-,]+)\//g)]
    .flatMap((x) => x[1].split(","))
    .filter(Boolean);
  return { m, modules: [...new Set(modules)] };
}

/** Build candidate bundle URLs for a broad module set. */
function buildUrls(boot) {
  const urls = [];
  const m = boot.m;
  if (m && m.length >= 4) {
    const [k, ck, am, rs] = m;
    // Ask for the full known superset via /exm= so we get the mapcore modules
    const mods = boot.modules.length ? boot.modules : DEFAULT_MODULES;
    urls.push(`${BASE}/maps/_/js/k=${k}/ck=${ck}/am=${am}/rt=j/d=1/exm=${mods.join(",")}/ed=1/rs=${rs}/m=sVzmUe`);
    urls.push(`${BASE}/maps/_/js/k=${k}/ck=${ck}/am=${am}/rt=j/d=1/rs=${rs}/m=${mods.join(",")}`);
  }
  // fallback: known-shape request if parsing failed
  if (!urls.length) {
    urls.push(`${BASE}/maps/_/js/k=maps.m.id.dyKVSrBemNw.2021.O/ck=maps.m.0noL2bKx98I.L.W.O/am=EGQAAADCUQAg/rt=j/d=1/exm=${DEFAULT_MODULES.join(",")}/ed=1/rs=ACT90oEhk8NN0DwvUkVyq69QZ3nloiUBpw/m=sVzmUe`);
  }
  return urls;
}

const DEFAULT_MODULES = ["AlIQtb","B863O","CoC10","DLBbMb","EUHafb","F0BtVb","GfLzUe","Gkme1d","HTJhQe","I23EXd","Inrkcf","ItB2Fd","J877qc","JayB4b","JxdeQb","KHTQfc","LsiLPd","MBT6he","MD5Ei","MJcXSb","MzGkHd","O0suJc","O3VRSe","OGUxO","P2V3Ge","P4xkRc","P7EDEc","R5Ivbf","RFjZgc","RGSME","RQcZid","RSts0d","Rq2f7d","RqNez","Rx7PMe","S8LFQc","SNyxle","SuCOhe","Tl5Isc","TyljBc","UMeTvf","UO66zf","WEtKm","WQJzF","WSq6zc","WneRFf","Z2jjYe","ZnXz4","b","b8h8i","bEpRLd","brB9Nc","cQ25Ub","cZ2KIb","d9cPQc","doYA8b","eBAeSb","eH4Qrd","eZ8p7d","fI6ZSb","fTMPl","hS8mff","iDMycd","ipMP5e","jF2zFd","jHreCd","kLe0lc","l2VXjc","luylmf","n836Cc","nhd0U","oakvDe","oiN24e","oiN7Y","pZSuFc","pa5s8b","qcugXe","qsXHac","rOE8I","rOuecf","rn1hub","ryLBnf","tNOPW","uA7o6c","uKtl4","vCLCu","vMe2Rc","woLgmd","x1Qcxb","xG6K7","xZZYUd","y9Fhge","yTZzPb","ypKQ1","zApwpe","znJTF"];

/** Scan JS text for the two constants. */
function scan(js) {
  const found = { programId: null, apiKey: null };

  for (const re of [
    /[.,]\s*(?:vg|w)\([a-zA-Z_$]+,\s*1,\s*["']([A-Za-z0-9_\-]{12,})["']\)/g,
    /\.U\(\s*["']c["']\s*,\s*["']([A-Za-z0-9_\-]{12,})["']/g,
  ]) {
    const m = js.match(re);
    if (m) { for (const s of m) { const v = s.match(/["']([A-Za-z0-9_\-]{12,})["']/)[1]; found.programId = found.programId || v; } }
  }

  const keyRe = /["']X-Goog-Api-Key["']\s*:\s*["'](AIza[0-9A-Za-z_\-]+)["']/g;
  for (const m of js.matchAll(keyRe)) {
    const ctx = js.slice(Math.max(0, m.index - 4000), m.index + 4000);
    if (/waa-pa\.clients6\.google\.com/.test(ctx)) { found.apiKey = m[1]; break; }
    if (!found.apiKey) found.apiKey = m[1];
  }
  return found;
}

async function discover(urls) {
  for (const u of urls) {
    let js;
    try { js = await get(u); } catch (e) { console.error("  skip:", e.message); continue; }
    const f = scan(js);
    if (f.programId && f.apiKey) return f;
    if (f.programId || f.apiKey)
      console.error("  partial:", JSON.stringify(f), "in", u.slice(0, 80));
  }
  // last resort: try known-shape fallback URL
  return null;
}

if (require.main === module) {
  (async () => {
    let urls = process.argv.slice(2);
    if (!urls.length) {
      console.error("→ bootstrapping from https://www.google.com/maps/ ...");
      const boot = await bootstrap();
      console.error(`  modules seen: ${boot.modules.length}`);
      urls = buildUrls(boot);
    }
    console.error(`→ scanning ${urls.length} candidate bundle(s) ...`);
    const res = await discover(urls);
    if (res && res.programId && res.apiKey) {
      console.log("=== DISCOVERY RESULT ===");
      console.log("PROGRAM_ID  :", res.programId);
      console.log("WAA_API_KEY :", res.apiKey);
      console.log("\n--- paste into bgkey.js ---");
      console.log(`const PROGRAM_ID = "${res.programId}";`);
      console.log(`const WAA_API_KEY = "${res.apiKey}";`);
    } else {
      console.log("Could not find both constants.");
      console.log("Fallback: open https://www.google.com/maps/ in DevTools,");
      console.log("Network tab, filter 'js', copy all /maps/_/js/... URLs, then:");
      console.log("  node discover_waa.js <url1> <url2> ...");
      process.exit(2);
    }
  })().catch((e) => { console.error("ERROR:", e.message); process.exit(1); });
}
