// HeartFlow arm of the three-way erasure measurement — RUN, do not read-and-conclude.
//
//   HF_ROOT=<clone of yun520-1/mark-heartflow-skill> node erasure_runtime_heartflow.js
//
// RESULT 2026-07-29: NOT_COMPUTABLE, and that is a limit of THIS instrument, not a finding about
// HeartFlow. memory-bank._doSave() calls encryptJSON() before writing, so the store is AES-encrypted
// at rest and a plaintext sentinel scan structurally cannot find the value — before OR after a
// delete. The precondition catches that instead of reporting a false "removed".
//
// THREE THINGS I GOT WRONG BY READING INSTEAD OF RUNNING, all of which fell in HeartFlow's favour:
//   1. I concluded from src/memory/forgetting.js (844 lines, Ebbinghaus decay, ARCHIVE maxAge:
//      Infinity) that HeartFlow archives rather than deletes. Nothing in src/ imports that module.
//      I reasoned from dead code.
//   2. The wired path is memory-bank.forget(), which calls this.memories.delete(id) and rewrites the
//      file. That is real removal, the opposite of what I claimed.
//   3. It encrypts at rest, which neither of the other two systems does. The key lives at
//      memory/.aes-key (0o600), so this is encryption against file theft, not against the operator —
//      state it that precisely if it is ever cited.
//
// Sequence of harness bugs before this ran at all, each caught by the NOT_COMPUTABLE branch rather
// than blamed on the peer: wrong require path, then bank.add() (the API is deposit()), then wrong
// constructor options. Read the API; do not guess it.

// Runtime arm: does HeartFlow's real forget() remove the VALUE from disk?
// Uses memory-bank.forget() -- the path actually wired in. forgetting.js (the 844-line Ebbinghaus
// module cited publicly) is imported by nothing in src/, so it is not the mechanism in play.
const fs = require('fs'), os = require('os'), path = require('path');
const SENT = 'ZQX' + Math.random().toString(16).slice(2) + Date.now().toString(16) + 'QZX';
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hf_'));
function onDisk(root, tok) {
  const hits = [];
  (function walk(d) { for (const e of fs.readdirSync(d, {withFileTypes:true})) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else { try { if (fs.readFileSync(p).includes(tok)) hits.push(path.relative(root, p)); } catch(_) {} }
  }})(root); return hits;
}
(async () => {
  const { MemoryBank } = require(process.env.HF_ROOT + '/src/memory/memory-bank.js');
  const bank = new MemoryBank({ dataDir: dir, storePath: path.join(dir, 'mb.json'), baseDir: dir });
  if (bank.load) await bank.load();
  const sid = bank.startSession ? await bank.startSession('probe') : null;
  // LEARNED layer, not CORE — forget() skips core by design, so testing core would be a rigged test
  await bank.deposit(`recovery phrase ${SENT}`, { layer: 'learned', sessionId: sid });
  await bank.save();
  const before = onDisk(dir, SENT);
  if (!before.length) return console.log(JSON.stringify(
    {verdict:'NOT_COMPUTABLE', why:'PRECONDITION FAILED: value never reached disk — OUR harness, not their system'}));
  const rep = bank.forget(1.0);      // prune everything below max strength
  await bank.save();
  const after = onDisk(dir, SENT);
  console.log(JSON.stringify({system:'HeartFlow memory-bank.forget()', report: rep,
    files_before: before, files_after: after,
    verdict: after.length ? 'VALUE REMAINS ON DISK' : 'VALUE REMOVED'}, null, 1));
})().catch(e => console.log(JSON.stringify({verdict:'NOT_COMPUTABLE', why:'OUR harness: '+String(e.message).slice(0,200)})));
