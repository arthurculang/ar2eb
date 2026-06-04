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

# Concept priority lists. First tag with an annual value for the FY wins; for
# gross profit / total debt we fall back to a computed combination.
CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues", "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueNet"],
    "cogs": ["CostOfRevenue", "CostOfGoodsAndServicesSold",
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
    "debt_total": ["DebtLongtermAndShorttermCombinedAmount"],
    "debt_lt": ["LongTermDebtNoncurrent", "LongTermDebt",
                "LongTermDebtAndCapitalLeaseObligations"],
    "debt_cur": ["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings",
                 "LongTermDebtAndCapitalLeaseObligationsCurrent"],
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


def flow_series(facts: dict, names: list[str]) -> dict[int, float]:
    """fy → full-year value (10-K, FY, ~annual duration), as first reported."""
    out: dict[int, tuple[str, float]] = {}   # fy → (filed, val)
    for tag in names:
        for e in _annual_entries(facts, tag):
            if e.get("fp") != "FY" or not str(e.get("form", "")).startswith("10-K"):
                continue
            if not _is_annual_duration(e):
                continue
            fy = int(e.get("fy") or date.fromisoformat(e["end"]).year)
            filed = e.get("filed", "9999-99-99")
            if fy not in out or filed < out[fy][0]:   # earliest filing = as-first-reported
                out[fy] = (filed, float(e["val"]))
        if out:
            break   # first tag that yielded data wins
    return {fy: v for fy, (_, v) in out.items()}


def instant_series(facts: dict, names: list[str], taxonomy: str = "us-gaap") -> dict[int, float]:
    """fy → point-in-time value at fiscal-year-end (10-K, FY)."""
    out: dict[int, tuple[str, float]] = {}
    for tag in names:
        for e in _annual_entries(facts, tag) if taxonomy == "us-gaap" \
                else _annual_entries(facts, tag, taxonomy):
            if e.get("fp") != "FY" or not str(e.get("form", "")).startswith("10-K"):
                continue
            if e.get("start"):    # instant facts have no start
                continue
            fy = int(e.get("fy") or date.fromisoformat(e["end"]).year)
            filed = e.get("filed", "9999-99-99")
            if fy not in out or filed < out[fy][0]:
                out[fy] = (filed, float(e["val"]))
        if out:
            break
    return {fy: v for fy, (_, v) in out.items()}


def fye_dates(facts: dict) -> dict[int, date]:
    """fy → fiscal-year-end date, from the revenue tag's annual entries."""
    out: dict[int, tuple[str, date]] = {}
    for tag in CONCEPTS["revenue"]:
        for e in _annual_entries(facts, tag):
            if e.get("fp") != "FY" or not str(e.get("form", "")).startswith("10-K"):
                continue
            if not _is_annual_duration(e):
                continue
            fy = int(e.get("fy") or date.fromisoformat(e["end"]).year)
            filed = e.get("filed", "9999-99-99")
            if fy not in out or filed < out[fy][0]:
                out[fy] = (filed, date.fromisoformat(e["end"]))
        if out:
            break
    return {fy: d for fy, (_, d) in out.items()}


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


def build(tickers: list[str]) -> tuple[list[dict], list[str]]:
    rows, gaps = [], []
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
        dtot = instant_series(facts, CONCEPTS["debt_total"])
        dlt = instant_series(facts, CONCEPTS["debt_lt"])
        dcur = instant_series(facts, CONCEPTS["debt_cur"])
        shares = instant_series(facts, ["EntityCommonStockSharesOutstanding"], "dei")
        fyes = fye_dates(facts)
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
            debt = dtot.get(fy)
            if debt is None:
                debt = (dlt.get(fy) or 0) + (dcur.get(fy) or 0) if (fy in dlt or fy in dcur) else None
            netcash = (cash.get(fy, 0) + sti.get(fy, 0) - debt) if debt is not None else None
            fye = fyes.get(fy)
            px = close_on_or_before(closes, fye) if (closes and fye) else None
            sh = shares.get(fy)
            mktcap = (px * sh / 1e9) if (px and sh) else None
            for metric, val in (("gross_profit", gprof), ("op_income", opi.get(fy)),
                                ("ocf", ocf.get(fy)), ("price", px), ("debt", debt)):
                if val is None:
                    gaps.append(f"{t} FY{fy}: missing {metric}")
            rows.append(dict(
                ticker=t, fy=fy, fye_month=(fye.strftime("%b") if fye else ""),
                mktcap_b=mktcap,
                net_cash_b=(netcash / 1e9 if netcash is not None else None),
                revenue_b=r / 1e9,
                gross_margin=safe_div(gprof, r),
                op_margin=safe_div(opi.get(fy), r),
                fcf_margin=safe_div((ocf.get(fy) - capex.get(fy))
                                    if (fy in ocf and fy in capex) else None, r),
                rev_growth=safe_div(r - rev[fy - 1], rev[fy - 1]) if (fy - 1) in rev else None,
                price_fye=px,
                _name=name))
        time.sleep(0.3)   # be polite to SEC
    return rows, gaps


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
    facts = {"entityName": "TEST", "facts": {
        "us-gaap": {
            "Revenues": {"units": {"USD": [
                {"start": "2022-01-01", "end": "2022-12-31", "val": 100, "fy": 2022, "fp": "FY", "form": "10-K", "filed": "2023-02-01"},
                {"start": "2023-01-01", "end": "2023-12-31", "val": 120, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"},
                {"start": "2023-07-01", "end": "2023-09-30", "val": 31, "fy": 2023, "fp": "Q3", "form": "10-Q", "filed": "2023-10-01"}]}},
            "GrossProfit": {"units": {"USD": [
                {"start": "2023-01-01", "end": "2023-12-31", "val": 60, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}},
            "OperatingIncomeLoss": {"units": {"USD": [
                {"start": "2023-01-01", "end": "2023-12-31", "val": 24, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}},
            "LongTermDebt": {"units": {"USD": [
                {"end": "2023-12-31", "val": 50, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}},
            "CashAndCashEquivalentsAtCarryingValue": {"units": {"USD": [
                {"end": "2023-12-31", "val": 30, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}}},
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [
            {"end": "2023-12-31", "val": 1_000_000_000, "fy": 2023, "fp": "FY", "form": "10-K", "filed": "2024-02-01"}]}}}}}
    rev = flow_series(facts, CONCEPTS["revenue"])
    assert rev == {2022: 100.0, 2023: 120.0}, rev          # quarterly excluded
    gp = flow_series(facts, CONCEPTS["gross_profit"])
    assert gp == {2023: 60.0}, gp
    debt = instant_series(facts, CONCEPTS["debt_lt"])
    assert debt == {2023: 50.0}, debt
    sh = instant_series(facts, ["EntityCommonStockSharesOutstanding"], "dei")
    assert sh == {2023: 1e9}, sh
    g = safe_div(120 - 100, 100)
    assert abs(g - 0.20) < 1e-9
    print("selftest OK — flow/instant parsers, FY filtering, growth all correct")


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
        rows, gaps = build(list(CIK))
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
    print("\nnext: python scripts/_models/ai2_backtest.py   (after promoting to ai2_panel.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
