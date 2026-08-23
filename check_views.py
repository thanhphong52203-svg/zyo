from curl_cffi import requests
import re

session = requests.Session(impersonate='chrome124')
r = session.get('https://zyo.lol/thanhphong.xq')
print("Status:", r.status_code)

with open('d:/zyo/thanhphong_dump.html', 'w', encoding='utf-8') as f:
    f.write(r.text)

# Look for view indicators in HTML
m_view = re.search(r'zyoViewProofConfig\s*=\s*(\{.*?\});', r.text, re.DOTALL)
if m_view:
    print("\n[+] zyoViewProofConfig:")
    print(m_view.group(1))

m_ana = re.search(r'zyoAnalyticsConfig\s*=\s*(\{.*?\});', r.text, re.DOTALL)
if m_ana:
    print("\n[+] zyoAnalyticsConfig:")
    print(m_ana.group(1)[:500])

# Look for data-tippy-content, badge, uid, etc.
tippys = re.findall(r'data-tippy-content=[\'"](.*?)[\'"]', r.text)
print("\n[+] data-tippy-contents found:")
for t in tippys:
    print(" -", t)

# Look for numbers near icons or views
views_elements = re.findall(r'<[^>]+(?:views?|badge|counter|header|stat)[^>]*>([^<]+)<', r.text, re.IGNORECASE)
print("\n[+] Text in view/badge/counter tags:")
for ve in views_elements:
    if ve.strip():
        print(" -", repr(ve.strip()))
