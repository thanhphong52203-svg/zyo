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
// 1. Overwrite webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 2. Mock plugins & languages
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

// 3. Mock chrome runtime
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};
"""

async def execute_turnstile_handshake(worker_id: int, cycle: int):
    print(f"\n[Worker {worker_id:02d}] --- Starting Cycle {cycle} ---", flush=True)

    chrome_path = r'C:\Program Files\Google\Chrome\Application\chrome.exe' if os.path.exists(r'C:\Program Files\Google\Chrome\Application\chrome.exe') else None

    async with async_playwright() as p:
        launch_kwargs = {
            # In Xvfb virtual display, headless=False runs as a real headed browser
            'headless': False if os.getenv("DISPLAY") or chrome_path else True,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=1366,768',
                '--mute-audio'
            ]
        }
        if chrome_path:
            launch_kwargs['executable_path'] = chrome_path

        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768},
            locale="en-US"
        )
        page = await context.new_page()
        await page.add_init_script(STEALTH_EVASION_JS)

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
            await page.goto(TARGET_URL, timeout=25000, wait_until="domcontentloaded")

            # Human-like interaction emulation
            await page.mouse.move(random.randint(150, 450), random.randint(150, 350))
            await asyncio.sleep(0.5)
            await page.mouse.wheel(0, random.randint(100, 250))

            print(f"[Worker {worker_id:02d}] Awaiting Turnstile resolution (up to 20s)...", flush=True)
            status, body = await asyncio.wait_for(res_future, timeout=20.0)
            print(f"[Worker {worker_id:02d}] [+] RESPONSE (HTTP {status}): {body.strip()}", flush=True)
            if "success\":true" in body or "counted\":true" in body:
                success = True
        except asyncio.TimeoutError:
            print(f"[Worker {worker_id:02d}] [-] Timeout waiting for view_count resolution", flush=True)
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
        await asyncio.sleep(random.uniform(3.0, 6.0))

    print(f"\n[Worker {worker_id:02d}] Finished. Successful Handshakes: {success_count}/{total_cycles}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
