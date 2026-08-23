import asyncio
import os
import random
import re
import sys
import time
from playwright.async_api import async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TARGET_USER = os.getenv("TARGET_USER", "thanhphong.xq")
TARGET_URL = f"https://zyo.lol/{TARGET_USER}"

STEALTH_EVASION_JS = """
// Overwrite the 'navigator.webdriver' property
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

// Mock languages and plugins
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});

// Mock window.chrome
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

// Mock permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
"""

async def execute_turnstile_handshake(worker_id: int, cycle: int):
    print(f"\n[Worker {worker_id:02d}] --- Starting Cycle {cycle} ---", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=1366,768',
                '--disable-gpu',
                '--disable-dev-shm-usage',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--mute-audio'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768},
            locale="en-US",
            timezone_id="America/New_York"
        )
        page = await context.new_page()
        await page.add_init_script(STEALTH_EVASION_JS)

        # Monitor page logs & errors
        page.on("console", lambda msg: print(f"[Worker {worker_id:02d}][Console] {msg.text[:120]}", flush=True) if "zyo" in msg.text.lower() or "error" in msg.text.lower() or "turnstile" in msg.text.lower() else None)
        page.on("pageerror", lambda err: print(f"[Worker {worker_id:02d}][PageError] {err}", flush=True))

        res_future = asyncio.get_event_loop().create_future()

        async def on_response(res):
            if 'php/api/view_count' in res.url and not res_future.done():
                try:
                    text = await res.text()
                    res_future.set_result((res.status, text))
                except Exception as e:
                    res_future.set_result((res.status, str(e)))

        page.on('response', on_response)

        success = False
        try:
            print(f"[Worker {worker_id:02d}] Navigating to {TARGET_URL}...", flush=True)
            await page.goto(TARGET_URL, timeout=40000, wait_until="networkidle")

            # Human-like interaction emulation
            await page.mouse.move(random.randint(150, 450), random.randint(150, 350))
            await asyncio.sleep(random.uniform(0.5, 1.0))
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # Explicitly wait for Turnstile iframe and resolution
            print(f"[Worker {worker_id:02d}] Awaiting Turnstile execution (up to 25s)...", flush=True)
            status, body = await asyncio.wait_for(res_future, timeout=25.0)
            print(f"[Worker {worker_id:02d}] [+] RESPONSE (HTTP {status}): {body.strip()}", flush=True)
            if "success\":true" in body or "counted\":true" in body:
                success = True
        except asyncio.TimeoutError:
            print(f"[Worker {worker_id:02d}] [-] Timeout waiting for view_count resolution", flush=True)
            # Inspect Turnstile container state in page
            try:
                state = await page.evaluate("() => ({ proofConfig: !!window.zyoViewProofConfig, turnstile: !!window.turnstile, proofPromise: !!window.zyoViewProofPromise })")
                print(f"[Worker {worker_id:02d}] [Debug State] {state}", flush=True)
            except Exception:
                pass
        except Exception as e:
            print(f"[Worker {worker_id:02d}] [-] Error: {e}", flush=True)
        finally:
            await page.close()
            await context.close()
            await browser.close()

    return success

async def main():
    worker_id = int(os.getenv("WORKER_ID", "1"))
    total_cycles = int(os.getenv("CYCLES", "3"))
    print(f"==================================================", flush=True)
    print(f"[*] SOVEREIGN CLUSTER WORKER {worker_id:02d} INITIALIZED", flush=True)
    print(f"[*] Target Profile: {TARGET_URL}", flush=True)
    print(f"[*] Target Cycles: {total_cycles}", flush=True)
    print(f"==================================================", flush=True)

    success_count = 0
    for cycle in range(1, total_cycles + 1):
        ok = await execute_turnstile_handshake(worker_id, cycle)
        if ok:
            success_count += 1
        await asyncio.sleep(random.uniform(4.0, 8.0))

    print(f"\n[Worker {worker_id:02d}] Finished. Successful Handshakes: {success_count}/{total_cycles}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
