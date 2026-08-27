"""团房成功订单 → 渠道订单 缓存映射生成脚本

数据来源：飞书电子表格 sheet OAiP8B 的 Channel Booking Number 列（102 个渠道订单号），
通过 MCP booking.channelbooking_v2 按 number 字段查询，获取 clientid / clientbd /
didahotelname_en(酒店英文名) / kpipriceusd(TTV) / kpirevenueusd(GP) / 国家 / 城市 等字段。

匹配规则：
- 团单号：从 clientreference 中提取最长数字串（≥5 位）
- 酒店名称：使用 MCP 的 didahotelname_en（按渠道订单号 number 直接匹配）
客户名称使用 MCP 的 clientid（非 CSV 客户名称），并加入 clientbd 作为 BD。

━━━ 数据来源 ━━━
- 渠道订单号清单：飞书电子表格 sheet OAiP8B（Channel Booking Number 列）
- 渠道订单详情：MCP execute_sql 查询 booking.channelbooking_v2 WHERE number IN (...)

━━━ MCP 查询 SQL（供未来重新生成时参考）━━━
SELECT number, clientreference, clientid, clientbd,
       kpipriceusd, kpirevenueusd,
       didahotelname_en,
       didahotelcountryname_cn, didahoteldestinationname_cn
FROM booking.channelbooking_v2
WHERE number IN ('<飞书 sheet OAiP8B 中的渠道订单号列表>')

━━━ 输出格式 ━━━
{
  "<团单号>": [
    {
      "渠道订单号": "<number>",
      "客户名称": "<clientid>",
      "BD": "<clientbd>",
      "酒店名称": "<didahotelname_en>",
      "TTV": <kpipriceusd or null>,
      "GP": <kpirevenueusd or null>,
      "GP%": <GP/TTV*100 or null>,
      "国家": "<didahotelcountryname_cn>",
      "城市": "<didahoteldestinationname_cn>"
    }, ...
  ]
}
团单号取自 clientreference 中的最长数字串（≥5 位）；无有效数字串的行归入 "" 键。

━━━ 执行方式 ━━━
本脚本读取 _mcp_channel_data.json（由 agent 通过 run_mcp 查询后保存的原始行），
匹配后写入 group_success_mapping.json。重新生成步骤：
1. 运行 _fetch_feishu_numbers.py 获取飞书 sheet OAiP8B 的渠道订单号
2. 通过 run_mcp execute_sql 按 number IN (...) 查询，结果保存到 _mcp_channel_data.json
3. 运行 python generate_success_mapping.py
"""
import os
import re
import json

# MCP 原始数据文件（由 agent 通过 run_mcp 查询后保存）
MCP_DATA_FILE = "_mcp_channel_data.json"
# 输出缓存文件
OUTPUT_FILE = "group_success_mapping.json"


def _to_num(val):
    """安全转换为 float，失败返回 None"""
    try:
        if val is None or str(val).strip() == "" or str(val).strip().lower() == "nan":
            return None
        return float(val)
    except (ValueError, TypeError):
        return None


def extract_group_id(clientreference):
    """从 clientreference 提取最长数字串（≥5 位）作为团单号，无则返回空串"""
    if not clientreference or not isinstance(clientreference, str):
        return ""
    digits = re.findall(r"\d+", clientreference)
    long_digits = [d for d in digits if len(d) >= 5]
    if not long_digits:
        return ""
    return max(long_digits, key=len)


def build_mapping():
    """构建团单号 → 渠道订单列表 映射"""
    if not os.path.exists(MCP_DATA_FILE):
        print(f"[生成映射] 未找到 MCP 数据文件 {MCP_DATA_FILE}，输出空映射")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return

    with open(MCP_DATA_FILE, "r", encoding="utf-8") as f:
        mcp_rows = json.load(f)

    print(f"[生成映射] MCP 渠道订单数据共 {len(mcp_rows)} 条")

    mapping = {}
    no_ref_count = 0
    matched_rows = 0

    for row in mcp_rows:
        gid = extract_group_id(row.get("clientreference", ""))
        if not gid:
            no_ref_count += 1
            gid = ""  # 无团单号的归入空键

        ttv = _to_num(row.get("kpipriceusd"))
        gp = _to_num(row.get("kpirevenueusd"))
        gp_pct = round(gp / ttv * 100, 2) if (ttv and gp is not None and ttv > 0) else None
        country = row.get("didahotelcountryname_cn") or ""
        city = row.get("didahoteldestinationname_cn") or ""

        entry = {
            "渠道订单号": str(row.get("number", "")).strip(),
            "客户名称": row.get("clientid", "") or "",
            "BD": row.get("clientbd", "") or "",
            "酒店名称": row.get("didahotelname_en", "") or "",
            "TTV": round(ttv, 2) if ttv is not None else None,
            "GP": round(gp, 2) if gp is not None else None,
            "GP%": gp_pct,
            "国家": country,
            "城市": city,
        }

        if gid not in mapping:
            mapping[gid] = []
        mapping[gid].append(entry)
        matched_rows += 1

    # 写入缓存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    # 统计
    real_keys = [k for k in mapping if k]
    print(f"[生成映射] 有团单号匹配的: {len(real_keys)} 个, 无团单号的: {no_ref_count} 条")
    print(f"[生成映射] 渠道订单总数: {matched_rows}")
    for gid, entries in mapping.items():
        if not gid:
            continue
        ttv_sum = sum(e["TTV"] or 0 for e in entries)
        print(f"  团单号 {gid}: {len(entries)} 条渠道订单, TTV合计 ${ttv_sum:,.2f}")
    print(f"[生成映射] 已写入 {OUTPUT_FILE}")


if __name__ == "__main__":
    build_mapping()
