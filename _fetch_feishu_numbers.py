"""Fetch channel booking numbers from Feishu sheet OAiP8B"""
from config import get_tenant_token, _parse_feishu_cell, load_feishu_config
import requests
import json

cfg = load_feishu_config()
token = get_tenant_token(cfg["app_id"], cfg["app_secret"])
spt = cfg["spreadsheet_token"]
url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spt}/values/OAiP8B"
resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
res = resp.json()
values = res["data"]["valueRange"]["values"]
nums = [_parse_feishu_cell(r[0]) for r in values[1:] if r and r[0]]
nums = [n.strip() for n in nums if n and n.strip()]
print("Total channel booking numbers:", len(nums))
print("Sample:", nums[:5])
with open("_feishu_channel_numbers.json", "w", encoding="utf-8") as f:
    json.dump(nums, f, ensure_ascii=False)
print("Saved to _feishu_channel_numbers.json")
