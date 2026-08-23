import asyncio
import hashlib
import json
import os
import random
import re
import sys
import time
from playwright.async_api import async_playwright
from curl_cffi.requests import AsyncSession
from curl_cffi import requests

sys.stdout.reconfigure(encoding="utf-8")

BANNER = r"""
███████╗██╗   ██╗ ██████╗     ████████╗██╗   ██╗██████╗ ███╗   ██╗███████╗████████╗██╗██╗     ███████╗
╚══███╔╝╚██╗ ██╔╝██╔═══██╗    ╚══██╔══╝██║   ██║██╔══██╗████╗  ██║██╔════╝╚══██╔══╝██║██║     ██╔════╝
  ███╔╝  ╚████╔╝ ██║   ██║       ██║   ██║   ██║██████╔╝██╔██╗ ██║███████╗   ██║   ██║██║     █████╗  
 ███╔╝    ╚██╔╝  ██║   ██║       ██║   ██║   ██║██╔══██╗██║╚██╗██║╚════██║   ██║   ██║██║     ██╔══╝  
███████╗   ██║   ╚██████╔╝       ██║   ╚██████╔╝██║  ██║██║ ╚████║███████║   ██║   ██║███████╗███████╗
╚══════╝   ╚═╝    ╚═════╝        ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝╚══════╝╚══════╝
        >> SOVEREIGN VERIFIED TURNSTILE VIEW CLUSTER ENGINE v4.0 <<
"""

DEFAULT_TARGET = "thanhphong.xq"

if len(sys.argv) > 1:
    raw_target = sys.argv[1].strip()
    if "zyo.lol/" in raw_target:
        TARGET_USER = raw_target.split("zyo.lol/")[-1].strip("/ ")
    else:
        TARGET_USER = raw_target
else:
    TARGET_USER = DEFAULT_TARGET

TARGET_URL = f"https://zyo.lol/{TARGET_USER}"

STATS = {
    "verified_views": 0,
    "failed_views": 0,
    "initial_views": "unknown",
    "current_views": "unknown",
    "start_time": time.time()
}

def check_views():
    try:
        r = requests.get(TARGET_URL, impersonate='chrome124', timeout=8)
        vm = re.search(r'data-tippy-content="Profile Views"[^>]*>.*?<p class="text">([^<]+)</p>', r.text, re.DOTALL)
        return vm.group(1).strip() if vm else 'unknown'
    except:
        return 'unknown'

async def fetch_working_proxies(max_needed=20):
    print("[*] Gathering candidate proxies for Turnstile Cluster...", flush=True)
    sources = [
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    ]
    candidates = []
    async with AsyncSession(impersonate="chrome124", timeout=6) as s:
        for u in sources:
            try:
                r = await s.get(u)
                for line in r.text.splitlines()[:100]:
                    line = line.strip()
                    if line and ":" in line:
                        candidates.append(f"http://{line}")
            except:
                pass

    random.shuffle(candidates)
    working = []

    async def verify_p(p):
        try:
            async with AsyncSession(impersonate="chrome124", proxies={"http": p, "https": p}, timeout=5) as s:
                r = await s.get("https://zyo.lol", timeout=5)
                if r.status_code == 200:
                    working.append(p)
                    print(f"  [+] Active Proxy for Turnstile: {p}", flush=True)
        except:
            pass

    chunk = candidates[:60]
    await asyncio.gather(*[verify_p(p) for p in chunk])
    print(f"[+] Total Verified Proxies Ready: {len(working)}", flush=True)
    return working

async def execute_turnstile_view(browser, proxy_url=None):
    context_kwargs = {
        'user_agent': random.choice([
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        ]),
        'viewport': {'width': 1200, 'height': 800}
    }
    if proxy_url:
        context_kwargs['proxy'] = {'server': proxy_url}

    context = await browser.new_context(**context_kwargs)
    page = await context.new_page()
    await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

    view_future = asyncio.get_event_loop().create_future()

    async def on_response(res):
        if 'php/api/view_count' in res.url and not view_future.done():
            try:
                body = await res.text()
                view_future.set_result((res.status, body))
            except Exception as e:
                view_future.set_result((res.status, str(e)))

    page.on('response', on_response)

    success = False
    try:
        await page.goto(TARGET_URL, timeout=22000)

        # Micro interactions to simulate real human visit
        await page.mouse.move(random.randint(100, 400), random.randint(100, 300))
        await asyncio.sleep(0.3)
        await page.mouse.wheel(0, random.randint(80, 200))

        # Wait for view_count submission (up to 15s)
        status, body = await asyncio.wait_for(view_future, timeout=15.0)
        if status == 200 and ("success" in body.lower() or "true" in body.lower()):
            success = True
            STATS["verified_views"] += 1
            print(f"[+] [SUCCESS] HTTP {status} -> {body.strip()}", flush=True)
        else:
            STATS["failed_views"] += 1
            print(f"[-] [REJECT] HTTP {status} -> {body.strip()}", flush=True)
    except Exception as e:
        STATS["failed_views"] += 1
        print(f"[-] [TIMEOUT/ERR] {e}", flush=True)
    finally:
        await page.close()
        await context.close()

    return success

async def cluster_runner():
    print(BANNER, flush=True)
    print(f"[*] Target Profile: {TARGET_URL}", flush=True)
    init_v = check_views()
    STATS["initial_views"] = init_v
    STATS["current_views"] = init_v
    print(f"[+] Initial Profile Views: {init_v}", flush=True)
    print(f"==================================================================", flush=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--window-size=1200,800',
                '--mute-audio'
            ]
        )

        cycle = 0
        while True:
            cycle += 1
            print(f"\n[*] --- Cluster Iteration {cycle} ---", flush=True)
            
            # Fetch batch of working proxies if needed
            proxies = await fetch_working_proxies(max_needed=10)
            if not proxies:
                proxies = [None] # Direct fallback

            for proxy in proxies[:8]:
                p_label = proxy.split('://')[-1] if proxy else "Direct Host"
                print(f"[*] Dispatching view session via {p_label}...", flush=True)
                await execute_turnstile_view(browser, proxy)
                await asyncio.sleep(random.uniform(1.5, 3.0))

            current_v = check_views()
            STATS["current_views"] = current_v
            elapsed = time.time() - STATS["start_time"]
            print(f"\n" + "="*70, flush=True)
            print(f"[PROGRESS] Iteration: {cycle} | Live Views: {current_v} (Init: {STATS['initial_views']}) | Elapsed: {int(elapsed)}s", flush=True)
            print(f"[PROGRESS] Total Verified View Handshakes: {STATS['verified_views']} | Failed: {STATS['failed_views']}", flush=True)
            print("="*70 + "\n", flush=True)
            await asyncio.sleep(3)

if __name__ == '__main__':
    try:
        asyncio.run(cluster_runner())
    except KeyboardInterrupt:
        print("\n[*] Turnstile Cluster stopped by user.")
