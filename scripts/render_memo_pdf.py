#!/usr/bin/env python3
"""Render a memo PDF from the JSX print harness (Phase 1 pipeline).

Starts a temporary HTTP server on a random port serving public/, opens
print.html?ticker=<slug> in Playwright Chromium, waits for React to mount
and fonts to load (signalled via document.body.dataset.ready), then prints
to PDF at 14"x8.5" landscape — matching the current memo.py output.

The harness deliberately mirrors public/index.html's no-build React+Babel-
in-the-browser pattern so the same JSX runs in both web preview and PDF.

Usage:
    python scripts/render_memo_pdf.py <ticker>
    # writes out/<ticker>-memo__phase1.pdf
"""
from __future__ import annotations

import http.server
import os
import socket
import socketserver
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PUBLIC = REPO / "public"
OUT = REPO / "out"

# Playwright in this environment ships Chromium 1194 at a fixed path.
# Honoring PLAYWRIGHT_CHROMIUM_PATH lets you override per-environment.
CHROMIUM_PATH = os.environ.get(
    "PLAYWRIGHT_CHROMIUM_PATH",
    "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
)


class _Handler(http.server.SimpleHTTPRequestHandler):
    # Silent — don't spam stdout with every asset request.
    def log_message(self, *_args):
        pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve_public(port: int) -> socketserver.ThreadingTCPServer:
    server = socketserver.ThreadingTCPServer(
        ("127.0.0.1", port),
        lambda *a, **kw: _Handler(*a, directory=str(PUBLIC), **kw),
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _stamped_filename(ticker: str) -> str:
    import yaml
    st = yaml.safe_load((REPO / "data" / f"{ticker}.yml").read_text())["stamp"]
    return f"{ticker}-memo__v{st['pdf_version']}__{st['pdf_timestamp']}.pdf"


def render(ticker: str, out_path: Path | None = None) -> Path:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(exist_ok=True)
    if out_path is None:
        # Use the stamped filename from data/<ticker>.yml so output lands at
        # the canonical name that public/memos/ expects.
        out_path = OUT / _stamped_filename(ticker)
    out_pdf = out_path

    port = _free_port()
    server = _serve_public(port)
    url = f"http://127.0.0.1:{port}/print.html?ticker={ticker}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROMIUM_PATH)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            # Wait for memo_pdf.jsx to signal ready (fonts loaded + React mounted)
            page.wait_for_function(
                "document.body.dataset.ready === '1'", timeout=15_000
            )
            # Spec §3.5 A safe-zones: every .memo-page must keep its content
            # inside the page height AND clear of the footer band. Two distinct
            # failure modes:
            #   (1) page-boundary overflow — content runs past the bottom of
            #       the 8.5in page (scrollHeight > clientHeight). overflow:hidden
            #       clips it; the reader loses information off the page edge.
            #   (2) footer-band intrusion — content sits within the page but
            #       behind the opaque footer band (position:absolute, bottom:0).
            #       scrollHeight stays within bounds so (1) misses it, yet the
            #       footer's paper background visually truncates the content
            #       (e.g. ISRG page-1 scenario-card headlines, May 2026). The
            #       footer is the .memo-footer element; any in-flow content whose
            #       bottom crosses the footer's top edge is masked.
            # Both surface on every render; STRICT_LAYOUT=1 turns them into
            # errors (CI / pre-merge). Default warn-only so rebuild_all.py
            # doesn't break on legacy bleeds.
            overflows = page.evaluate("""() => {
                const TOL_PX = 2;
                const out = [];
                document.querySelectorAll('.memo-page').forEach((pg, i) => {
                    const issues = [];
                    // (1) page-boundary overflow
                    const bleed = pg.scrollHeight - pg.clientHeight;
                    if (bleed > TOL_PX) issues.push(`overflows page bottom by ${bleed}px`);
                    // (2) footer-band intrusion
                    const footer = pg.querySelector('.memo-footer');
                    if (footer) {
                        const pgTop = pg.getBoundingClientRect().top;
                        const footTop = footer.getBoundingClientRect().top - pgTop;
                        // Max bottom of any in-flow content NOT inside the footer.
                        let maxBottom = 0;
                        pg.querySelectorAll('*').forEach(el => {
                            if (el === footer || footer.contains(el)) return;
                            if (!(el.textContent || '').trim()) return;
                            const b = el.getBoundingClientRect().bottom - pgTop;
                            if (b > maxBottom) maxBottom = b;
                        });
                        const intrude = Math.round(maxBottom - footTop);
                        if (intrude > TOL_PX) {
                            issues.push(`content hidden behind footer band by ${intrude}px (footer top ${Math.round(footTop)}px)`);
                        }
                    }
                    if (issues.length) out.push({ page: i + 1, issues });
                });
                return out;
            }""")
            if overflows:
                strict = os.environ.get("STRICT_LAYOUT") == "1"
                tag = "ERROR" if strict else "warn"
                lines = "\n".join(
                    f"    page {o['page']}: {'; '.join(o['issues'])}"
                    for o in overflows
                )
                print(
                    f"[{ticker}] {tag}: layout safe-zone violation:\n{lines}\n"
                    "  spec §3.5 A: content must stay inside the page AND clear "
                    "of the footer band. Trim narrative / rowGap / fontSize. "
                    "(set STRICT_LAYOUT=1 to fail)",
                    file=sys.stderr,
                )
                if strict:
                    browser.close()
                    raise SystemExit(2)

            # (3) horizontal SVG-clip — chart <text> whose box runs past its
            # own <svg> viewBox left/right edge gets cut at the SVG viewport.
            # The (1)/(2) checks above are page-level and don't see this. Every
            # chart margin/title now sizes from its label widths (spec §3.5:
            # estSvgTextWidth / monoTextWidth / niceStep / wrapSvgText), so this
            # is a STRICT gate like (1)/(2). TOL ignores sub-unit pokes (2px,
            # matching the page-overflow tolerance).
            hclips = page.evaluate("""() => {
                const TOL = 2.0; const out = [];
                document.querySelectorAll('svg').forEach((svg) => {
                    const vb = svg.viewBox.baseVal;
                    if (!vb || !vb.width) return;
                    svg.querySelectorAll('text').forEach((t) => {
                        let bb; try { bb = t.getBBox(); } catch (e) { return; }
                        if (!(t.textContent || '').trim()) return;
                        const right = bb.x + bb.width;
                        if (right > vb.width + TOL) {
                            out.push(`right +${(right - vb.width).toFixed(0)}px: ${(t.textContent||'').trim().slice(0,28)}`);
                        } else if (bb.x < vb.x - TOL) {
                            out.push(`left ${(bb.x - vb.x).toFixed(0)}px: ${(t.textContent||'').trim().slice(0,28)}`);
                        }
                    });
                });
                return out;
            }""")
            if hclips:
                strict = os.environ.get("STRICT_LAYOUT") == "1"
                tag = "ERROR" if strict else "warn"
                shown = "\n".join(f"    {h}" for h in hclips[:8])
                more = f"\n    … +{len(hclips) - 8} more" if len(hclips) > 8 else ""
                print(
                    f"[{ticker}] {tag}: {len(hclips)} chart label(s) clip at the "
                    f"SVG edge:\n{shown}{more}\n"
                    "  spec §3.5: size the chart's margin from the label width "
                    "(see estSvgTextWidth / monoTextWidth). (set STRICT_LAYOUT=1 to fail)",
                    file=sys.stderr,
                )
                if strict:
                    browser.close()
                    raise SystemExit(2)
            page.pdf(
                path=str(out_pdf),
                width="14in",
                height="8.5in",
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                print_background=True,
                prefer_css_page_size=True,
            )
            browser.close()
    finally:
        server.shutdown()
        server.server_close()

    return out_pdf


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/render_memo_pdf.py <ticker>", file=sys.stderr)
        return 1
    ticker = sys.argv[1].lower()
    out = render(ticker)
    size_kb = out.stat().st_size / 1024
    print(f"wrote {out.relative_to(REPO)} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
