"""Membership-cost layer for mnemo corroboration — make a *corroborating source* costly or impossible to
mint, so "two distinct sources" stops being free.

mnemo's corroboration bar (`_is_corroborated` / `_distinct_sources`) counts DISTINCT canonical source
strings. `_canon_source` collapses host-variants of ONE origin, but two genuinely different strings
('evil-a.example', 'evil-b.example') count as two independent sources for FREE. That is the Sybil hole
Douceur (2002) formalized: with no cost to mint an identity, corroboration ("N independent sources agree")
is forgeable by one actor wearing N hats. No downstream integrity/IFC/low-water-mark gate fixes it, because
they all rest on the same forgeable independence.

This module makes identity SCARCE. A `Membership` decides whether a source identifier counts as an
independent, costly-to-mint identity; mnemo's gate counts a source toward corroboration only if it is
`admits()`-ed. Four backends, each a different Sybil-resistance mechanism from the literature:

  OpenMembership  — the current mnemo behavior: any string counts (free). The baseline / the hole.
  Registrar       — a certifying authority: the canon must sit in a trusted allowlist (Douceur's
                    "trusted agency certifies identities" — the one path he proves defeats Sybil).
  Attestation     — an unforgeable credential: the source presents a signature over its identity that
                    verifies against an ISSUER key it does not control (Myers&Liskov DLM authority root).
                    Zero-dep crypto stand-in = HMAC-SHA256 (symmetric: models "the issuer signed this";
                    swap in Ed25519 for a real asymmetric deployment — see mnemo agent-receipts).
  ProofOfWork     — a resource cost: the source presents a hashcash proof of `bits` difficulty binding its
                    identity. Minting K identities costs ~K * 2**bits hashes. Real, permissionless, but a
                    SYMMETRIC tax (honest writers pay it too) that a resourced attacker simply pays.
  StakedStanding  — an economic bond: the source posts stake, its live standing decays and is SLASHED on
                    bad-credit outcomes; it counts only while standing >= `min_stake`. A Sybil must lock
                    capital per forged identity and forfeits it when detected — the jacksonxly staked/
                    decaying-standing idea, made real. This is the only backend with a non-by-construction
                    frontier: deterrence holds iff expected forfeiture (detect_prob * stake) >= damage.

Zero-dependency (hashlib/hmac from the stdlib). Deterministic. MIT. Dogfood-first (mnemo's own gate).
Roots: Douceur 2002 (Sybil), Myers&Liskov DLM POPL 1997, Biba 1977, CaMeL 2503.18813; framing/staked
standing credited to jacksonxly (r/LangChain)."""
import hashlib
import hmac
import re

# Reuse mnemo's own entity-resolution so a Membership sees the SAME canonical key the corroboration gate does
# (host-variant sybils already collapsed before we even ask whether the identity is costly).
try:
    from inspeximus import Inspeximus
    _canon = Inspeximus._canon_source
except Exception:                                    # standalone use without the package importable
    def _canon(doc) -> str:
        s = str(doc or "").strip().lower()
        s = re.sub(r"^[a-z]+://", "", s)
        s = re.sub(r"^www\.", "", s)
        s = s.split("/")[0].split("?")[0]
        s = re.sub(r"\.(org|com|net|io|gov|edu|co|ai|dev|info|news)$", "", s)
        s = re.sub(r"[^a-z0-9]+", "", s)
        return s


def _leading_zero_bits(digest: bytes) -> int:
    """Number of leading zero BITS in a byte digest (hashcash difficulty measure)."""
    n = 0
    for byte in digest:
        if byte == 0:
            n += 8
            continue
        # count leading zeros within this byte, then stop
        b = byte
        while b < 0x80:
            n += 1
            b <<= 1
        break
    return n


class Membership:
    """Decide whether a source identity counts as an independent, costly-to-mint corroborator."""
    kind = "base"

    def admits(self, canon: str, cred: dict | None) -> bool:
        raise NotImplementedError

    def mint_cost(self) -> str:
        """Human-readable cost, per identity, to an attacker who wants this source to COUNT."""
        return "unknown"


class OpenMembership(Membership):
    """The current mnemo behavior and the baseline: any source string counts. Free to mint => Sybil-open."""
    kind = "open"

    def admits(self, canon, cred=None):
        return True

    def mint_cost(self):
        return "free (any string) — the Sybil hole"


class Registrar(Membership):
    """A trusted certifying authority: only canons in the signed allowlist count. Defeats Sybil BY
    CONSTRUCTION (Douceur's proven path) at the price of relocating trust to the registrar and requiring
    a real-world registration step — it is permissioned, not permissionless."""
    kind = "registrar"

    def __init__(self, allow):
        self.allow = {_canon(a) for a in (allow or [])}

    def admits(self, canon, cred=None):
        return canon in self.allow

    def mint_cost(self):
        return "impossible without a registrar entry (real-world registration; trust relocated to the authority)"


class Attestation(Membership):
    """An unforgeable credential: the source must present a signature over its canon that verifies against
    an ISSUER key it does not hold. Sybil-defeating BY CONSTRUCTION *given the attacker lacks the issuer
    key*; the residual attack is compromising the issuer (one key => unlimited forged identities), so a
    real deployment must ALSO require >=2 DISTINCT issuers for a corroboration to count (see the gate).
    HMAC-SHA256 here is a zero-dep symmetric stand-in for a real asymmetric signature."""
    kind = "attestation"

    def __init__(self, issuer_key: bytes, issuer_id: str = "issuer"):
        self.k = issuer_key if isinstance(issuer_key, bytes) else str(issuer_key).encode()
        self.issuer_id = issuer_id

    def issue(self, canon: str) -> str:
        """The issuer signs an identity. An attacker without self.k cannot produce this for a new canon."""
        return hmac.new(self.k, canon.encode(), hashlib.sha256).hexdigest()

    def admits(self, canon, cred=None):
        sig = (cred or {}).get("attest")
        return bool(sig) and hmac.compare_digest(str(sig), self.issue(canon))

    def mint_cost(self):
        return "impossible without the issuer key (residual: compromise the issuer -> unlimited; require >=2 issuers)"


class ProofOfWork(Membership):
    """A resource cost: the source must present a nonce whose hash over its canon has >= `bits` leading
    zeros (hashcash). Permissionless and real, but a SYMMETRIC tax: the honest writer pays the same
    ~2**bits hashes per identity, and a resourced attacker just pays K times for K identities. Raises the
    Sybil floor, never removes it."""
    kind = "pow"

    def __init__(self, bits: int = 16):
        self.bits = int(bits)

    def admits(self, canon, cred=None):
        nonce = (cred or {}).get("pow")
        if nonce is None:
            return False
        h = hashlib.sha256(f"{canon}:{nonce}".encode()).digest()
        return _leading_zero_bits(h) >= self.bits

    def mint(self, canon: str):
        """Find a valid nonce. Returns (nonce, hashes_tried). BOTH honest and attacker call this."""
        n = 0
        while True:
            if _leading_zero_bits(hashlib.sha256(f"{canon}:{n}".encode()).digest()) >= self.bits:
                return n, n + 1
            n += 1

    def mint_cost(self):
        return f"~2**{self.bits} hashes per identity (SYMMETRIC: honest writers pay it too; resourced attacker pays K x)"


class StakedStanding(Membership):
    """An economic bond. A source posts `stake`; its live standing DECAYS each step and is SLASHED on a
    bad-credit outcome; it counts as a corroborator only while standing >= `min_stake`. A Sybil must lock
    real capital per forged identity and forfeits it on detection — so, unlike PoW, the cost is ASYMMETRIC:
    the honest writer keeps its stake, the detected attacker loses it. Deterrence is not by construction;
    it holds iff expected forfeiture (detection_prob * live_stake) >= damage extractable per poison, which
    is what the frontier probe measures. Credit: jacksonxly's staked/decaying standing."""
    kind = "stake"

    def __init__(self, min_stake: float = 1.0, decay: float = 0.98, slash_frac: float = 1.0):
        self.min_stake = float(min_stake)
        self.decay = float(decay)
        self.slash_frac = float(slash_frac)
        self._ledger: dict[str, float] = {}      # canon -> live standing

    def post(self, canon, stake: float):
        self._ledger[_canon(canon)] = self._ledger.get(_canon(canon), 0.0) + float(stake)

    def decay_all(self, steps: int = 1):
        for k in list(self._ledger):
            self._ledger[k] *= self.decay ** steps

    def slash(self, canon, frac: float | None = None):
        k = _canon(canon)
        f = self.slash_frac if frac is None else float(frac)
        self._ledger[k] = self._ledger.get(k, 0.0) * (1.0 - f)

    def standing(self, canon) -> float:
        return self._ledger.get(_canon(canon), 0.0)

    def admits(self, canon, cred=None):
        return self._ledger.get(canon, 0.0) >= self.min_stake

    def mint_cost(self):
        return (f"lock >= {self.min_stake} stake per identity, forfeited on detection "
                f"(ASYMMETRIC: honest keeps it, detected attacker loses it)")


def count_independent_sources(links, by_id, membership: Membership | None = None) -> int:
    """mnemo's `_distinct_sources`, gated by a membership-cost backend: count DISTINCT canonical sources
    among corroborating links, but only those the membership `admits()`. A source-less link still counts as
    its own id (no regression) UNLESS a membership is set that requires a credential — then an un-credentialed
    source does not count (that is the whole point: identity must be paid for). Backward-compatible: with
    membership=None or OpenMembership, this equals mnemo's current count exactly."""
    m = membership or OpenMembership()
    keys = set()
    for lid in (links or []):
        lr = by_id.get(lid)
        if lr is None:
            continue
        src = lr.get("source")
        doc = src.get("doc") if isinstance(src, dict) else (src if isinstance(src, str) else None)
        canon = _canon(doc) if doc else ("id:" + lid)
        cred = src.get("cred") if isinstance(src, dict) else None
        if m.admits(canon, cred):
            keys.add(canon)
    return len(keys)


def is_corroborated(rec: dict, by_id: dict, membership: Membership | None = None) -> bool:
    """mnemo's `_is_corroborated` with the membership-gated source count. Earned net-positive credit and an
    already-graduated 'semantic' memory still short-circuit (those are not source-count claims); the >=2
    distinct-source path is what the membership hardens."""
    good = float(rec.get("good", 0) or 0)
    bad = float(rec.get("bad", 0) or 0)
    if good > 0 and good >= bad:
        return True
    if rec.get("mtype") == "semantic":
        return True
    return count_independent_sources(rec.get("links"), by_id, membership) >= 2
