/**
 * prepare-public.cjs — runs as part of `npm run build` (before `vite build`).
 *
 * 1. Runs the Python pipeline: python3 ../scripts/build_loopboard.py
 *    Rebuilds web/public/data/*.json from the real resume corpus, proving the
 *    shipped payloads are pipeline-generated rather than hand-authored.
 * 2. Copies data/test-vectors.json into web/public/data/ (shared contract).
 * 3. Writes web/public/data/stamp.json with repo, git sha, UTC build time.
 * 4. Exits non-zero if the pipeline produced no shortlist.
 */
const { execFileSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const WEB_DIR = path.resolve(__dirname, "..");
const ROOT_DIR = path.resolve(WEB_DIR, "..");
const DATA_DIR = path.join(ROOT_DIR, "data");
const PUBLIC_DATA = path.join(WEB_DIR, "public", "data");

function fail(msg) {
  console.error(`prepare-public: ${msg}`);
  process.exit(1);
}

function gitSha() {
  try {
    return execFileSync("git", ["-C", ROOT_DIR, "rev-parse", "--short", "HEAD"], {
      encoding: "utf8",
    }).trim();
  } catch {
    return "unknown";
  }
}

console.log("prepare-public: running python3 ../scripts/build_loopboard.py ...");
try {
  execFileSync("python3", ["../scripts/build_loopboard.py"], {
    cwd: WEB_DIR,
    stdio: "inherit",
  });
} catch (e) {
  fail(`pipeline script failed (${e && e.message ? e.message : e})`);
}

const shortlist = path.join(PUBLIC_DATA, "shortlist.json");
if (!fs.existsSync(shortlist)) {
  fail("shortlist.json missing after pipeline run");
}
const rows = JSON.parse(fs.readFileSync(shortlist, "utf8"));
if (!Array.isArray(rows) || rows.length === 0) {
  fail("pipeline produced an empty shortlist");
}
console.log(`prepare-public: pipeline shortlisted ${rows.length} candidates`);

const vectors = path.join(DATA_DIR, "test-vectors.json");
if (fs.existsSync(vectors)) {
  fs.copyFileSync(vectors, path.join(PUBLIC_DATA, "test-vectors.json"));
  console.log("prepare-public: copied test-vectors.json");
}

const stamp = {
  repo: "ai-recruiting-coordinator",
  sha: gitSha(),
  builtAt: new Date().toISOString(),
  target: "ai-recruiting-coordinator.web.app",
};
fs.writeFileSync(
  path.join(PUBLIC_DATA, "stamp.json"),
  JSON.stringify(stamp, null, 2) + "\n",
);
console.log(`prepare-public: stamp written (sha=${stamp.sha})`);
console.log("prepare-public: done");
