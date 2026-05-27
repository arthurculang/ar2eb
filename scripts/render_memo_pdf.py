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
            # inside the page height. The CSS uses overflow:hidden + a paper-
            # colored footer band to mask small bleeds, but anything past the
            # footer band gets clipped — invisible content is worse than
            # truncated content. We surface overflows on every render so they
            # can't ship undetected. Set STRICT_LAYOUT=1 to turn them into
            # errors (use in CI / before merge). Default is warn-only so the
            # rebuild_all.py pipeline doesn't break on legacy bleeds (NAUT
            # page 2 ultra_bull column is a known pre-existing case).
            overflows = page.evaluate("""() => {
                const TOL_PX = 2;
                return Array.from(document.querySelectorAll('.memo-page')).map((el, i) => ({
                    page: i + 1,
                    scrollH: el.scrollHeight,
                    clientH: el.clientHeight,
                    bleed: el.scrollHeight - el.clientHeight,
                })).filter(p => p.bleed > TOL_PX);
            }""")
            if overflows:
                strict = os.environ.get("STRICT_LAYOUT") == "1"
                tag = "ERROR" if strict else "warn"
                lines = "\n".join(
                    f"    page {o['page']}: scrollH={o['scrollH']}px > clientH={o['clientH']}px (bleed {o['bleed']}px)"
                    for o in overflows
                )
                print(
                    f"[{ticker}] {tag}: content overflows page boundary:\n{lines}\n"
                    "  spec §3.5 A: content area must not extend past the "
                    "footer band. Trim narrative / rowGap / fontSize so the "
                    "page fits within 8.5in. (set STRICT_LAYOUT=1 to fail)",
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
