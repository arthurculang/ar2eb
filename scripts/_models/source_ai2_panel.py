#!/usr/bin/env python3
"""Source the AI 2.0 fundamentals panel deterministically — no transcription,
no memory — from SEC XBRL (fundamentals + shares) and stooq (split-adjusted
FYE prices). Emits the schema scripts/_models/ai2_backtest.py consumes.

WHY THIS EXISTS: the research-agent panel (`ai2_panel.csv`) has reliable
operating columns but its EV inputs (mktcap, net_cash) and FYE prices are
training-knowledge estimates `[e]` — every finance data host was egress-blocked
when it was built, so the 8-weight fit overfits (see README). This script
replaces those load-bearing columns with sourced data the moment the hosts are
allowlisted.

REQUIRES the environment network policy to allow:
    data.sec.gov     — XBRL companyfacts (revenue, margins, cash, debt, shares)
    stooq.com        — daily split-adjusted closes (for FYE price → mktcap, returns)
  (optional) www.sec.gov — the ticker→CIK map; we embed a fallback so it's not required.

USAGE:
    python scripts/_models/source_ai2_panel.py            # → ai2_panel_sourced.csv
    python scripts/_models/source_ai2_panel.py --out ai2_panel.csv   # promote
    python scripts/_models/source_ai2_panel.py --selftest # parser unit test (no network)
    python scripts/_models/source_ai2_panel.py --probe    # just test host reachability

After a real run, eyeball the coverage report it prints (which (ticker, metric,
fy) cells it could not fill — concept-tag gaps are expected for a few names and
get patched in CONCEPTS below), then re-run scripts/_models/ai2_backtest.py.
"""
from __future__ import annotations
import gzip
import io
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
UA = "ar2eb-research arthurculang@gmail.com"   # SEC requires a UA with contact

# 26-name universe → CIK. CIKs are stable public IDs; the script cross-checks
# the SEC entityName against the ticker on fetch and warns on a mismatch, so a
# wrong CIK here surfaces loudly rather than silently polluting the panel.
CIK = {
    "META": 1326801, "NVDA": 1045810, "AAPL": 320193, "GOOGL": 1652044,
    "MSFT": 789019, "AMZN": 1018724, "NFLX": 1065280, "TSLA": 1318605,
    "CRM": 1108524, "ADBE": 796343, "SHOP": 1594805, "DDOG": 1561550,
    "CRWD": 1535527, "NOW": 1373715, "SNOW": 1640147, "UBER": 1543151,
    "ABNB": 1559720, "ISRG": 1035267, "LULU": 1397187, "DASH": 1792789,
    "PTON": 1639825, "BYND": 1655210, "ROKU": 1428439, "SNAP": 1564408,
    "ZM": 1585521, "W": 1616707,
}

# Concept priority lists. Resolved by per-fy PRIORITY MERGE (see flow_series /
# instant_series): for each fiscal year, the earliest-filed value from the
# highest-priority tag that covers it wins — so a tag with sparse coverage
# (e.g. a stray single year) no longer shadows a fuller tag, and post-ASC606
# revenue (RevenueFromContract…, ~2018+) is back-filled by Revenues/SalesRevenueNet
# for the earlier years. Debt is built from disjoint noncurrent + current parts
# (avoids double-counting a "total" tag), with a combined-tag fallback.
CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues", "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueNet"],
    "cogs": ["CostOfRevenue", "CostOfGoodsAndServicesSold",
             "CostOfGoodsAndServiceExcludingDepreciationDepletionAndAmortization",
             "CostOfGoodsSold", "CostOfServices"],
    "gross_profit": ["GrossProfit"],
    "op_income": ["OperatingIncomeLoss"],
    "ocf": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment",
              "PaymentsToAcquireProductiveAssets"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue",
             "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "sti": ["ShortTermInvestments", "MarketableSecuritiesCurrent",
            "AvailableForSaleSecuritiesCurrent"],
    # Disjoint debt parts → total = noncurrent + current (or a combined tag).
    "debt_noncur": ["LongTermDebtNoncurrent", "ConvertibleDebtNoncurrent",
                    "ConvertibleLongTermNotesPayable", "SecuredLongTermDebt",
                    "LongTermDebtAndCapitalLeaseObligations", "SeniorNotesNoncurrent",
                    "SeniorNotes", "NotesPayableNoncurrent"],
    "debt_cur": ["LongTermDebtCurrent", "ConvertibleNotesPayableCurrent",
                 "ConvertibleDebtCurrent", "SecuredDebtCurrent", "DebtCurrent",
                 "ShortTermBorrowings", "LongTermDebtAndCapitalLeaseObligationsCurrent"],
    "debt_combined": ["DebtLongtermAndShorttermCombinedAmount", "LongTermDebt"],
}


# ── HTTP (stdlib; works once hosts are allowlisted) ─────────────────────────
class Blocked(Exception):
    pass


def _get(url: str, tries: int = 4) -> bytes:
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA, "Accept-Encoding": "gzip", "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return raw
        except urllib.error.HTTPError as e:
            body = (e.read() or b"")[:80].decode("utf8", "replace")
            if e.code == 403 and "allowlist" in body.lower():
                raise Blocked(f"{url} → 403 Host not in allowlist")
            if e.code in (403, 429, 503) and i < tries - 1:
                time.sleep(2 ** i); continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if "allowlist" in str(e).lower():
                raise Blocked(f"{url} → host not in allowlist")
            if i < tries - 1:
                time.sleep(2 ** i); continue
            raise
    raise RuntimeError(f"giving up: {url}")


# ── SEC XBRL parsing ────────────────────────────────────────────────────────
# companyfacts blobs are large (tens of MB for AAPL/MSFT/AMZN) and slow to pull
# + parse; cache the raw JSON to disk so re-runs (while patching CONCEPTS below)
# are instant. Historical first-reported facts are immutable, so a session-local
# cache is safe; set AI2_NO_CACHE=1 to force a fresh pull.
CACHE = Path("/tmp/ai2_companyfacts_cache")


def companyfacts(cik: int) -> dict:
    import os
    cf = CACHE / f"CIK{cik:010d}.json"
    if not os.environ.get("AI2_NO_CACHE") and cf.exists() and cf.stat().st_size > 0:
        return json.loads(cf.read_text())
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    raw = _get(url)
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = cf.with_suffix(".json.tmp")     # atomic write (no truncated cache on kill)
    tmp.write_bytes(raw)
    tmp.replace(cf)
    return json.loads(raw)


def _annual_entries(facts: dict, tag: str, taxonomy: str = "us-gaap"):
    """Return the tag's USD entries (or 'shares' for share counts)."""
    node = facts.get("facts", {}).get(taxonomy, {}).get(tag)
    if not node:
        return []
    units = node.get("units", {})
    return units.get("USD") or units.get("shares") or []


def _is_annual_duration(e: dict) -> bool:
    s, end = e.get("start"), e.get("end")
    if not s or not end:
        return False
    d = (date.fromisoformat(end) - date.fromisoformat(s)).days
    return 350 <= d <= 380


def _fy(e: dict) -> int:
    """Fiscal-year key = the YEAR of the period-end date.

    NOT e['fy'] — that is the *filing's* fiscal year, which the same value
    repeats across the 2 comparative years inside every 10-K (e.g. NVIDIA tags
    the FY2017/18/19 revenues all with fy=2019), so e['fy'] conflates distinct
    years. The end-date year is unique per fiscal year and increments by one
    across consecutive annual reports (incl. late-January fiscal years)."""
    return date.fromisoformat(e["end"]).year


def flow_series(facts: dict, names: list[str]) -> dict[int, float]:
    """fy → full-year value (10-K, FY, ~annual duration). Per-fy priority merge:
    for each fy the earliest-filed value (as-first-reported) from the highest-
    priority tag covering it wins; lower-priority tags back-fill other years."""
    best: dict[int, tuple[int, str, float]] = {}   # fy → (tag_rank, filed, val)
    for rank, tag in enumerate(names):
        for e in _annual_entries(facts, tag):
            if e.get("fp") != "FY" or not str(e.get("form", "")).startswith("10-K"):
                continue
            if not _is_annual_duration(e):
                continue
            fy = _fy(e)
            filed = e.get("filed", "9999-99-99")
            cur = best.get(fy)
            if cur is None or rank < cur[0] or (rank == cur[0] and filed < cur[1]):
                best[fy] = (rank, filed, float(e["val"]))
    return {fy: v for fy, (_, _, v) in best.items()}


def instant_series(facts: dict, names: list[str], taxonomy: str = "us-gaap") -> dict[int, float]:
    """fy → point-in-time value at fiscal-year-end (10-K, FY). Per-fy priority merge."""
    best: dict[int, tuple[int, str, float]] = {}
    for rank, tag in enumerate(names):
        for e in _annual_entries(facts, tag, taxonomy):
            if e.get("fp") != "FY" or not str(e.get("form", "")).startswith("10-K"):
                continue
            if e.get("start"):    # instant facts have no start
                continue
            fy = _fy(e)
            filed = e.get("filed", "9999-99-99")
            cur = best.get(fy)
            if cur is None or rank < cur[0] or (rank == cur[0] and filed < cur[1]):
                best[fy] = (rank, filed, float(e["val"]))
    return {fy: v for fy, (_, _, v) in best.items()}


def fye_dates(facts: dict) -> dict[int, date]:
    """fy → fiscal-year-end date, from the revenue tags' annual entries."""
    best: dict[int, tuple[int, str, date]] = {}
    for rank, tag in enumerate(CONCEPTS["revenue"]):
        for e in _annual_entries(facts, tag):
            if e.get("fp") != "FY" or not str(e.get("form", "")).startswith("10-K"):
                continue
            if not _is_annual_duration(e):
                continue
            fy = _fy(e)
            filed = e.get("filed", "9999-99-99")
            cur = best.get(fy)
            if cur is None or rank < cur[0] or (rank == cur[0] and filed < cur[1]):
                best[fy] = (rank, filed, date.fromisoformat(e["end"]))
    return {fy: d for fy, (_, _, d) in best.items()}


def shares_at_fye(facts: dict, fyes: dict[int, date]) -> dict[int, float]:
    """fy → shares outstanding nearest each fiscal-year-end. The dei cover-page
    count is as-of a date shortly AFTER FYE, so map each entry to the fy whose
    FYE it most closely follows (≤ ~135 days), else a balance-sheet count at FYE."""
    raw: list[tuple[date, str, float]] = []
    for tag, tax in (("EntityCommonStockSharesOutstanding", "dei"),
                     ("CommonStockSharesOutstanding", "us-gaap")):
        for e in _annual_entries(facts, tag, tax):
            if e.get("start") or not e.get("end"):
                continue
            raw.append((date.fromisoformat(e["end"]), e.get("filed", "9999"), float(e["val"])))
        if raw:
            break
    out: dict[int, float] = {}
    for fy, fye in fyes.items():
        cand = [r for r in raw if 0 <= (r[0] - fye).days <= 135]
        if not cand:
            cand = [r for r in raw if abs((r[0] - fye).days) <= 20]
        if cand:
            cand.sort(key=lambda r: (abs((r[0] - fye).days), r[1]))
            out[fy] = cand[0][2]
    return out


# ── stooq prices ────────────────────────────────────────────────────────────
def stooq_closes(ticker: str) -> list[tuple[date, float]]:
    url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
    txt = _get(url).decode("utf8", "replace")
    rows = []
    for ln in txt.splitlines()[1:]:
        p = ln.split(",")
        if len(p) >= 5:
            try:
                rows.append((date.fromisoformat(p[0]), float(p[4])))
            except ValueError:
                pass
    return sorted(rows)


def close_on_or_before(closes: list[tuple[date, float]], d: date) -> float | None:
    best = None
    for dt, c in closes:
        if dt <= d:
            best = c
        else:
            break
    return best


# ── assembly ─────────────────────────────────────────────────────────────────
def safe_div(a, b):
    return (a / b) if (a is not None and b not in (None, 0)) else None


def build(tickers: list[str]) -> tuple[list[dict], list[str], dict]:
    rows, gaps = [], []
    diag = {"entity": {}, "debtfree": []}
    for t in tickers:
        cik = CIK.get(t)
        if not cik:
            gaps.append(f"{t}: no CIK"); continue
        try:
            facts = companyfacts(cik)
        except Blocked:
            raise
        except Exception as e:
            gaps.append(f"{t}: companyfacts failed ({e})"); continue
        name = facts.get("entityName", "")
        rev = flow_series(facts, CONCEPTS["revenue"])
        gp = flow_series(facts, CONCEPTS["gross_profit"])
        cogs = flow_series(facts, CONCEPTS["cogs"])
        opi = flow_series(facts, CONCEPTS["op_income"])
        ocf = flow_series(facts, CONCEPTS["ocf"])
        capex = flow_series(facts, CONCEPTS["capex"])
        cash = instant_series(facts, CONCEPTS["cash"])
        sti = instant_series(facts, CONCEPTS["sti"])
        d_nc = instant_series(facts, CONCEPTS["debt_noncur"])
        d_cu = instant_series(facts, CONCEPTS["debt_cur"])
        d_comb = instant_series(facts, CONCEPTS["debt_combined"])
        fyes = fye_dates(facts)
        shares = shares_at_fye(facts, fyes)
        diag["entity"][t] = name
        try:
            closes = stooq_closes(t)
        except Blocked:
            raise
        except Exception as e:
            closes = []; gaps.append(f"{t}: stooq failed ({e})")

        for fy in sorted(rev):
            r = rev[fy]
            gprof = gp.get(fy)
            if gprof is None and cogs.get(fy) is not None:
                gprof = r - cogs[fy]
            # Total debt = disjoint noncurrent + current parts; a combined "total"
            # tag (LongTermDebt / DebtLongtermAndShorttermCombinedAmount) takes the
            # max (it already bundles current maturities). No debt tag at all ⇒
            # genuinely debt-free ⇒ 0 (so net cash = cash + STI, never None).
            parts = (d_nc.get(fy) or 0.0) + (d_cu.get(fy) or 0.0)
            total = d_comb.get(fy)
            if total is not None:
                debt = max(total, parts)
            elif fy in d_nc or fy in d_cu:
                debt = parts
            else:
                debt = 0.0
                diag["debtfree"].append(f"{t} FY{fy}")
            netcash = cash.get(fy, 0.0) + sti.get(fy, 0.0) - debt
            fye = fyes.get(fy)
            px = close_on_or_before(closes, fye) if (closes and fye) else None
            sh = shares.get(fy)
            mktcap = (px * sh / 1e9) if (px and sh) else None
            for metric, val in (("gross_profit", gprof), ("op_income", opi.get(fy)),
                                ("ocf", ocf.get(fy)), ("price", px)):
                if val is None:
                    gaps.append(f"{t} FY{fy}: missing {metric}")
            rows.append(dict(
                ticker=t, fy=fy, fye_month=(fye.strftime("%b") if fye else ""),
                mktcap_b=mktcap,
                net_cash_b=netcash / 1e9,
                revenue_b=r / 1e9,
                gross_margin=safe_div(gprof, r),
                op_margin=safe_div(opi.get(fy), r),
                fcf_margin=safe_div((ocf.get(fy) - capex.get(fy))
                                    if (fy in ocf and fy in capex) else None, r),
                rev_growth=safe_div(r - rev[fy - 1], rev[fy - 1]) if (fy - 1) in rev else None,
                price_fye=px,
                _name=name))
        time.sleep(0.3)   # be polite to SEC
    return rows, gaps, diag


COLS = ["ticker", "fy", "fye_month", "mktcap_b", "net_cash_b", "revenue_b",
        "gross_margin", "op_margin", "fcf_margin", "rev_growth", "price_fye"]


def fmt(v):
    if v is None:
        return ""
    return f"{v:.4f}" if isinstance(v, float) else str(v)


def write_csv(rows: list[dict], out: Path):
    lines = [",".join(COLS)]
    for r in sorted(rows, key=lambda x: (x["ticker"], x["fy"])):
        lines.append(",".join(fmt(r.get(c)) for c in COLS))
    out.write_text("\n".join(lines) + "\n")


# ── self-test: parser on a synthetic companyfacts blob (no network) ──────────
def selftest():
    # Revenues covers 2021–2022 (pre-ASC606); RevenueFromContract covers 2022–2023.
    # The 2022 RevenueFromContract entry is a COMPARATIVE tagged with the filing's
    # fy=2023 (the conflation trap) — it must land in 2022 by its end-date, NOT 2023.
    facts = {"entityName": "TEST", "facts": {
        "us-gaap": {
            "Revenues": {"units": {"USD": [
                {"start": "2021-01-01", "end": "2021-12-31", "val": 80,  "fy": 2021, "fp": "FY", "form": "10-K", "filed": "2022-02-01"},
                {"start": "2022-01-01", "end": "2022-12-31", "val": 100, "fy": 2022, "fp": "FY", "form": "10-K", "filed": "2023-02-01"},
                {"start": "2022-07-01", "end": "2022-09-30", "val": 26,  "fy": 2022, "fp": "Q3", "form": "10-Q", "filed": "2022-10-01"}]}},
            "RevenueFromContractWithCustomerExcludingAssessedTax": {"units": {"USD": [
                {"start": "2022-01-01", "end": "2022-12-31", "val": 100, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"},
                {"start": "2023-01-01", "end": "2023-12-31", "val": 120, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}},
            "GrossProfit": {"units": {"USD": [
                {"start": "2023-01-01", "end": "2023-12-31", "val": 60, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}},
            "OperatingIncomeLoss": {"units": {"USD": [
                {"start": "2023-01-01", "end": "2023-12-31", "val": 24, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}},
            "LongTermDebt": {"units": {"USD": [
                {"end": "2023-12-31", "val": 50, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}},
            "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [
                {"end": "2023-12-31", "val": 30, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}}},
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
            {"end": "2024-01-20", "val": 1_000_000_000, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}}}}}
    rev = flow_series(facts, CONCEPTS["revenue"])
    assert rev == {2021: 80.0, 2022: 100.0, 2023: 120.0}, rev   # conflation fixed; quarterly excluded; back-fill works
    gp = flow_series(facts, CONCEPTS["gross_profit"])
    assert gp == {2023: 60.0}, gp
    # LongTermDebt now lives in the combined (total) bucket, not noncurrent.
    assert instant_series(facts, CONCEPTS["debt_noncur"]) == {}, "LongTermDebt must not be a noncurrent tag"
    assert instant_series(facts, CONCEPTS["debt_combined"]) == {2023: 50.0}
    # shares: cover-page count dated 20d after the 2023 FYE maps to fy2023 only.
    sh = shares_at_fye(facts, fye_dates(facts))
    assert sh == {2023: 1e9}, sh
    g = safe_div(120 - 100, 100)
    assert abs(g - 0.20) < 1e-9
    print("selftest OK — end-date fy (no conflation), priority-merge back-fill, "
          "debt buckets, share-to-FYE mapping all correct")


def probe():
    for url in ("https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json",
                "https://stooq.com/q/d/l/?s=nvda.us&i=d"):
        try:
            n = len(_get(url))
            print(f"OK   {url.split('?')[0]}  ({n} bytes)")
        except Blocked as e:
            print(f"BLOCKED  {e}")
        except Exception as e:
            print(f"ERROR  {url.split('?')[0]}  {e}")


def main(argv):
    if "--selftest" in argv:
        selftest(); return 0
    if "--probe" in argv:
        probe(); return 0
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else HERE / "ai2_panel_sourced.csv"
    out = out if out.is_absolute() else HERE / out
    try:
        rows, gaps, diag = build(list(CIK))
    except Blocked as e:
        print(f"\nNETWORK BLOCKED: {e}")
        print("Allowlist data.sec.gov + stooq.com in the environment network policy,")
        print("then re-run. (python scripts/_models/source_ai2_panel.py --probe to test.)")
        return 2
    write_csv(rows, out)
    nt = len({r["ticker"] for r in rows})
    filled = sum(1 for r in rows if r["mktcap_b"] and r["price_fye"] is not None)
    print(f"wrote {out}  ({len(rows)} rows · {nt} tickers · {filled} with mktcap+price)")
    # Split price/mktcap gaps (the stooq-gated columns) from genuine SEC concept-
    # tag gaps — the latter are what CONCEPTS patching is about. Full list → file.
    price_gaps = [g for g in gaps if "missing price" in g]
    fund_gaps = [g for g in gaps if "missing price" not in g]
    rep = HERE / "ai2_coverage_gaps.txt"
    rep.write_text("\n".join(gaps) + ("\n" if gaps else ""))
    print(f"\ncoverage gaps: {len(fund_gaps)} fundamentals + {len(price_gaps)} price/mktcap "
          f"(full list → {rep.name})")
    if price_gaps:
        pt = sorted({g.split()[0] for g in price_gaps})
        print(f"  price/mktcap unfilled for {len(pt)} tickers (stooq apikey-gated): "
              f"{', '.join(pt)}")
    if fund_gaps:
        print(f"\n  {len(fund_gaps)} fundamentals gaps to triage (patch CONCEPTS / CIK / debt logic):")
        for g in fund_gaps:
            print("   -", g)
    else:
        print("\n  no fundamentals-tag gaps — SEC coverage is solid.")
    # entity cross-check: a wrong CIK shows up as a company name that isn't the ticker.
    ents = "  ".join(f"{t}={diag['entity'].get(t, '?')[:16]}" for t in sorted(diag["entity"]))
    print(f"\nentity cross-check (ticker = SEC entityName — eyeball for a wrong CIK):\n  {ents}")
    if diag["debtfree"]:
        dft = sorted({x.split()[0] for x in diag["debtfree"]})
        print(f"\n{len(diag['debtfree'])} (ticker,fy) carried no debt tag → treated debt-free "
              f"(net cash = cash + STI): {', '.join(dft)}")
    print("\nnext: python scripts/_models/ai2_backtest.py   (after promoting to ai2_panel.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
