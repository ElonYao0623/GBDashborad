"""Process MCP query results: merge all batches, extract rows, save _mcp_channel_data.json.

输入文件（三批 MCP 查询结果，均含 didahotelname_en 酒店英文名）：
- 批次1/2: toolcall-output 原始响应（前缀 "The MCP server responded with:"）
- 批次3:   已解码的 {"rows": [...]} JSON 文件
"""
import json

OUT_FILE = "_mcp_channel_data.json"

RAW_FILES = [
    r"C:\Users\DL\AppData\Local\Temp\trae\toolcall-output\5224e3bc-2016-49ea-a7f5-53e62173b866.txt",
    r"C:\Users\DL\AppData\Local\Temp\trae\toolcall-output\2966f698-103b-4a37-8243-315cb1e98547.txt",
    "_mcp_batch3_rows.json",
]


def parse_raw_response(raw):
    """解析 'The MCP server responded with: [{"type":"text","text":"..."}]' 格式"""
    idx = raw.find("[{")
    if idx == -1:
        raise ValueError("could not find JSON array in MCP response")
    outer_json = raw[idx:]
    outer_json = outer_json[: outer_json.rfind("]") + 1]
    outer = json.loads(outer_json)
    text_val = outer[0]["text"]
    return json.loads(text_val)


all_rows = []
for path in RAW_FILES:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if raw.lstrip().startswith("{"):
        data = json.loads(raw)          # 已是 {"rows": [...]} 结构
    else:
        data = parse_raw_response(raw)  # 原始 MCP 包裹格式
    rows = data.get("rows", [])
    print(f"{path}: {len(rows)} rows")
    all_rows.extend(rows)

print(f"Total merged rows: {len(all_rows)}")
if all_rows:
    keys = sorted(all_rows[0].keys())
    print("Sample row:", json.dumps(all_rows[0], ensure_ascii=False)[:200])

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_rows, f, ensure_ascii=False, indent=2)
print(f"Saved {len(all_rows)} rows to {OUT_FILE}")
