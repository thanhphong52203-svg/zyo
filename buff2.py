import asyncio
import hashlib
import json
import os
import random
import re
import sys
import time
from collections import defaultdict
from curl_cffi.requests import AsyncSession
from curl_cffi import requests

sys.stdout.reconfigure(encoding="utf-8")

# ==============================================================================
# COOK45 - ZYO.LOL ADVANCED SOVEREIGN VIEW & TRAFFIC ENGINE v4.2 (HYBRID OMEGA)
# ==============================================================================

BANNER = r"""
███████╗██╗   ██╗ ██████╗     ██╗      ██████╗ ██╗     
╚══███╔╝╚██╗ ██╔╝██╔═══██╗    ██║     ██╔═══██╗██║     
  ███╔╝  ╚████╔╝ ██║   ██║    ██║     ██║   ██║██║     
 ███╔╝    ╚██╔╝  ██║   ██║    ██║     ██║   ██║██║     
███████╗   ██║   ╚██████╔╝    ███████╗╚██████╔╝███████╗
╚══════╝   ╚═╝    ╚═════╝     ╚══════╝ ╚═════╝ ╚══════╝
    >> SOVEREIGN HIGH-SPEED VIEW & TRAFFIC ENGINE v4.2 <<
"""

# ==============================================================================
# TARGET CONFIGURATION & ARGUMENT PARSING
# ==============================================================================
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

# ==============================================================================
# GLOBAL STATE & STATISTICS
# ==============================================================================
VALID_PROXIES = set()
DEAD_PROXIES = set()
FAIL_COUNT = defaultdict(int)
PROXY_LOCK = asyncio.Lock()

STATS = {
    "requests_sent": 0,
    "success_views": 0,
    "analytics_sent": 0,
    "initial_views": "unknown",
    "current_views": "unknown",
    "target_uid": "unknown",
    "start_time": time.time(),
    "errors": 0
}

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/https.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/https.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/socks4.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/https.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/https/data.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/http.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/https.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/socks4.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/socks5.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
    "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/http.txt",
    "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/https.txt",
    "https://raw.githubusercontent.com/ErcinDedeoglu/free-proxy-list/main/proxies.txt",
    "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/UserR3X/Proxy-List/main/http.txt",
    "https://raw.githubusercontent.com/officialputuid/KangProxy/master/http.txt",
]

def validate_proxy(proxy: str) -> bool:
    if not re.match(r'^(http|https|socks4|socks5)://', proxy):
        return False
    parts = proxy.split('://')[1].split('@')[-1].split(':')
    if len(parts) != 2:
        return False
    ip, port = parts
    if not re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip):
        return False
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except ValueError:
        return False

def solve_pow(seed: str, difficulty: int = 18) -> str:
    """
    Fast SHA256 PoW Solver.
    """
    if not seed:
        return "0"
    nonce = 0
    while True:
        data = f"{seed}:{nonce}".encode('ascii')
        h = hashlib.sha256(data).digest()
        val = int.from_bytes(h[:4], 'big')
        if (val >> (32 - difficulty)) == 0:
            return str(nonce)
        nonce += 1

def parse_tokens(html: str):
    if not html:
        return None

    m_view = re.search(r'zyoViewProofConfig\s*=\s*(\{.*?\});', html, re.DOTALL)
    m_ana = re.search(r'zyoAnalyticsConfig\s*=\s*(\{.*?\});', html, re.DOTALL)

    uid = None
    if m_view:
        m_uid = re.search(r'userId\s*:\s*(\d+)', m_view.group(1))
        if m_uid: uid = int(m_uid.group(1))
    if not uid and m_ana:
        m_uid = re.search(r'profileUserId\s*:\s*(\d+)', m_ana.group(1))
        if m_uid: uid = int(m_uid.group(1))
    if not uid:
        m_uid = re.search(r'["\']?user_id["\']?\s*[:=]\s*(\d+)', html, re.IGNORECASE)
        if m_uid: uid = int(m_uid.group(1))

    ts = None
    if m_view:
        m_ts = re.search(r'timestamp\s*:\s*["\']?(\d+)["\']?', m_view.group(1))
        if m_ts: ts = m_ts.group(1)
    if not ts and m_ana:
        m_ts = re.search(r'timestamp\s*:\s*["\']?(\d+)["\']?', m_ana.group(1))
        if m_ts: ts = m_ts.group(1)
    if not ts:
        m_ts = re.search(r'timestamp\s*[:=]\s*["\']?(\d{10,13})["\']?', html, re.IGNORECASE)
        if m_ts: ts = m_ts.group(1)

    sign = None
    if m_view:
        m_sig = re.search(r'signature\s*:\s*["\']([a-f0-9]{64})["\']', m_view.group(1), re.IGNORECASE)
        if m_sig: sign = m_sig.group(1)
    if not sign:
        m_sig = re.search(r'(?:view_count|zyoViewProofConfig)[^;]*?["\']?signature["\']?\s*:\s*["\']([a-f0-9]{64})["\']', html, re.DOTALL | re.IGNORECASE)
        if m_sig: sign = m_sig.group(1)
    if not sign:
        m_sig = re.search(r'signature\s*[:=]\s*["\']([a-f0-9]{64})["\']', html, re.IGNORECASE)
        if m_sig: sign = m_sig.group(1)

    pow_seed = None
    pow_difficulty = 18
    pow_blob = None
    if m_view:
        m_seed = re.search(r'"seed"\s*:\s*"([^"]+)"', m_view.group(1))
        m_diff = re.search(r'"difficulty"\s*:\s*(\d+)', m_view.group(1))
        m_blob = re.search(r'"blob"\s*:\s*"([^"]+)"', m_view.group(1))
        if m_seed: pow_seed = m_seed.group(1)
        if m_diff: pow_difficulty = int(m_diff.group(1))
        if m_blob: pow_blob = m_blob.group(1)

    signatures = {}
    if m_ana:
        for sm in re.finditer(r'"([a-zA-Z0-9_]+)"\s*:\s*"([a-f0-9]{64})"', m_ana.group(1)):
            signatures[sm.group(1)] = sm.group(2)
    else:
        for sm in re.finditer(r'"(profile_view|link_click|widget_click|audio_play|discord_profile_click|second_tab_open|like)"\s*:\s*"([a-f0-9]{64})"', html):
            signatures[sm.group(1)] = sm.group(2)

    sign_view = signatures.get("profile_view", "")

    views_m = re.search(r'data-tippy-content="Profile Views"[^>]*>.*?<p class="text">([^<]+)</p>', html, re.DOTALL)
    current_views = views_m.group(1).strip() if views_m else "unknown"

    if not ts or not uid or (not sign and not sign_view):
        return None

    return {
        "uid": uid,
        "ts": ts,
        "sign": sign or sign_view,
        "sign_view": sign_view,
        "pow_seed": pow_seed,
        "pow_difficulty": pow_difficulty,
        "pow_blob": pow_blob or "",
        "signatures": signatures,
        "current_views": current_views
    }

def get_current_views():
    try:
        r = requests.get(TARGET_URL, impersonate='chrome124', timeout=8)
        vm = re.search(r'data-tippy-content="Profile Views"[^>]*>.*?<p class="text">([^<]+)</p>', r.text, re.DOTALL)
        return vm.group(1).strip() if vm else 'unknown'
    except:
        return 'unknown'

# ==============================================================================
# PROXY MANAGER
# ==============================================================================

async def load_proxies():
    global VALID_PROXIES, DEAD_PROXIES, FAIL_COUNT
    async with PROXY_LOCK:
        print("[*] Scraping fresh proxy lists across 30+ providers...", flush=True)
        new_proxies = set()
        seen_ips = set()
        
        if os.path.exists("proxies.txt"):
            try:
                with open("proxies.txt", "r", encoding="utf-8") as pf:
                    for line in pf:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if not re.match(r'^(http|https|socks4|socks5)://', line):
                            line = f"http://{line}"
                        if validate_proxy(line):
                            new_proxies.add(line)
                print(f"[+] Loaded custom proxies from proxies.txt", flush=True)
            except Exception:
                pass

        async with AsyncSession(impersonate="chrome124", timeout=6) as s:
            async def fetch_source(url):
                try:
                    r = await s.get(url, timeout=6)
                    if r.status_code != 200:
                        return
                    ip_pattern = re.compile(
                        r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
                        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?):'
                        r'(?:[1-9]\d{0,4}|[1-5]\d{4}|6[0-4]\d{3}|65[0-4]\d{2}|655[0-2]\d|6553[0-5])\b'
                    )
                    ips = ip_pattern.findall(r.text)
                    url_lower = url.lower()
                    if "socks5" in url_lower:
                        proto = "socks5"
                    elif "socks4" in url_lower:
                        proto = "socks4"
                    elif "https" in url_lower:
                        proto = "https"
                    else:
                        proto = "http"
                    
                    for ip in ips:
                        if ip in DEAD_PROXIES:
                            continue
                        ip_only = ip.split(':')[0]
                        if ip_only in seen_ips:
                            continue
                        proxy = f"{proto}://{ip}"
                        if validate_proxy(proxy):
                            new_proxies.add(proxy)
                            seen_ips.add(ip_only)
                except Exception:
                    pass

            await asyncio.gather(*[fetch_source(u) for u in PROXY_SOURCES])

        for proxy in new_proxies:
            if validate_proxy(proxy):
                VALID_PROXIES.add(proxy)

        print(f"[+] Total Active Proxies In Pool: {len(VALID_PROXIES)}", flush=True)

# ==============================================================================
# ASYNC DISTRIBUTED WORKER
# ==============================================================================

async def worker(worker_id: int):
    browsers = [
        "chrome124", "chrome123", "chrome120", "chrome119",
        "safari17_0", "safari16_5", "chrome_android", "safari_ios"
    ]

    referrers = [
        "https://www.google.com/search?q=zyo+lol+",
        "https://www.tiktok.com/",
        "https://discord.com/",
        "https://twitter.com/",
        "https://instagram.com/",
        "https://facebook.com/"
    ]

    while True:
        async with PROXY_LOCK:
            if len(VALID_PROXIES) < 5:
                await asyncio.sleep(2)
                continue
            
            proxy_list = list(VALID_PROXIES)
            random.shuffle(proxy_list)
            proxy_list.sort(key=lambda x: FAIL_COUNT.get(x, 0))
            proxy = random.choice(proxy_list[:min(100, len(proxy_list))])
        
        if proxy.startswith("socks5://"):
            proxies = {"http": proxy, "https": proxy, "socks5": proxy}
        elif proxy.startswith("socks4://"):
            proxies = {"http": proxy, "https": proxy, "socks4": proxy}
        else:
            proxies = {"http": proxy, "https": proxy}

        success = False
        browser = random.choice(browsers)
        ref = random.choice(referrers) + str(random.randint(100, 99999))

        try:
            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": random.choice(["vi-VN,vi;q=0.9,en-US;q=0.8", "en-US,en;q=0.9"]),
                "Accept-Encoding": "gzip, deflate, br",
                "Upgrade-Insecure-Requests": "1",
                "Referer": ref,
                "Sec-Ch-Ua-Platform": '"Windows"'
            }
            
            async with AsyncSession(
                impersonate=browser,
                proxies=proxies,
                timeout=5,
                allow_redirects=True,
                headers=headers
            ) as s:
                r_home = await s.get(TARGET_URL, timeout=5)
                if r_home.status_code != 200:
                    raise Exception(f"HTTP {r_home.status_code}")
                
                tok = parse_tokens(r_home.text)
                if not tok:
                    raise Exception("Failed to parse bio tokens")
                
                STATS["current_views"] = tok["current_views"]
                STATS["target_uid"] = tok["uid"]

                pow_nonce = solve_pow(tok["pow_seed"], tok.get("pow_difficulty", 18)) if tok.get("pow_seed") else ""
                
                # 1. Post view count
                r_view = await s.post(
                    "https://zyo.lol/php/api/view_count",
                    json={
                        "user_id": tok["uid"],
                        "pow_blob": tok["pow_blob"],
                        "pow_nonce": pow_nonce,
                        "turnstile_token": ""
                    },
                    headers={
                        "Content-Type": "application/json",
                        "X-Timestamp": tok["ts"],
                        "X-Sign": tok["sign"],
                        "Origin": "https://zyo.lol",
                        "Referer": TARGET_URL
                    },
                    timeout=4
                )
                
                STATS["requests_sent"] += 1

                # 2. Post realistic user analytics event
                if tok.get("signatures"):
                    ev_type = random.choice(["link_click", "widget_click", "audio_play", "second_tab_open"])
                    if ev_type in tok["signatures"]:
                        await asyncio.sleep(random.uniform(0.02, 0.08))
                        try:
                            await s.post(
                                "https://zyo.lol/php/api/analytics_event",
                                json={
                                    "profile_user_id": tok["uid"],
                                    "viewer_user_id": 0,
                                    "timestamp": tok["ts"],
                                    "events": [{
                                        "event_type": ev_type,
                                        "target_type": "link" if "link" in ev_type else "widget",
                                        "target_id": TARGET_URL,
                                        "event_count": 1,
                                        "metadata": {"referrer": ref}
                                    }],
                                    "signatures": tok["signatures"]
                                },
                                headers={
                                    "Content-Type": "application/json",
                                    "X-Timestamp": tok["ts"],
                                    "X-Sign": tok["signatures"][ev_type],
                                    "Origin": "https://zyo.lol",
                                    "Referer": TARGET_URL
                                },
                                timeout=4
                            )
                            STATS["analytics_sent"] += 1
                        except Exception:
                            pass
                
                if r_view.status_code == 200:
                    STATS["success_views"] += 1
                    clean_proxy = proxy.split("://")[-1][:22]
                    print(f"[+] [W-{worker_id:02d}] {clean_proxy:<22} [{browser:<14}] -> {r_view.text.strip()}", flush=True)
                    success = True
                    async with PROXY_LOCK:
                        FAIL_COUNT[proxy] = 0

        except Exception:
            STATS["errors"] += 1

        if not success:
            async with PROXY_LOCK:
                FAIL_COUNT[proxy] += 1
                if FAIL_COUNT[proxy] >= 2:
                    VALID_PROXIES.discard(proxy)
                    DEAD_PROXIES.add(proxy)

        await asyncio.sleep(random.uniform(0.01, 0.05))

# ==============================================================================
# MONITORING & REFRESH
# ==============================================================================

async def stats_monitor():
    while True:
        await asyncio.sleep(8)
        live_views = get_current_views()
        STATS["current_views"] = live_views
        elapsed = time.time() - STATS["start_time"]
        req_rate = STATS["requests_sent"] / max(1, elapsed) * 60
        succ_rate = STATS["success_views"] / max(1, elapsed) * 60
        async with PROXY_LOCK:
            active_p = len(VALID_PROXIES)
        
        print(f"\n" + "="*75, flush=True)
        print(f"[DASHBOARD] Target: {TARGET_URL} (UID: {STATS['target_uid']}) | Live Views: {live_views} (Init: {STATS['initial_views']})", flush=True)
        print(f"[DASHBOARD] Requests: {STATS['requests_sent']} | Success Pings: {STATS['success_views']} ({succ_rate:.1f}/min) | Analytics: {STATS['analytics_sent']}", flush=True)
        print(f"[DASHBOARD] Active Proxies: {active_p} | Engine Speed: {req_rate:.1f} req/min | Runtime: {int(elapsed)}s", flush=True)
        print("="*75 + "\n", flush=True)

async def proxy_refresher():
    while True:
        await asyncio.sleep(45)
        async with PROXY_LOCK:
            count = len(VALID_PROXIES)
        if count < 300:
            print(f"[!] Low proxy count ({count}), refreshing pool...", flush=True)
            await load_proxies()

# ==============================================================================
# MAIN RUNNER
# ==============================================================================

async def main():
    print(BANNER, flush=True)
    print(f"[*] Target Profile: {TARGET_URL}", flush=True)
    
    init_views = get_current_views()
    STATS["initial_views"] = init_views
    STATS["current_views"] = init_views
    print(f"[+] Initial Profile Views: {init_views}", flush=True)
    print(f"==================================================================", flush=True)

    await load_proxies()

    num_workers = 45
    print(f"[*] Spawning {num_workers} Sovereign Distributed Workers...", flush=True)

    tasks = [
        asyncio.create_task(proxy_refresher()),
        asyncio.create_task(stats_monitor())
    ]
    for i in range(num_workers):
        tasks.append(asyncio.create_task(worker(i + 1)))

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Sovereign Engine stopped by user.")