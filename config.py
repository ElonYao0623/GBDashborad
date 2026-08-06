import requests
import pandas as pd
import json
import os
from datetime import datetime

# 数据存储文件路径
DATA_FILE = "团房数据.csv"

# 订单状态双语映射
STATUS_WORKFLOW_MAP = {
    "customer_inquiry": {"zh": "客户咨询", "en": "Customer Inquiry"},
    "awaiting_joy_quotation": {"zh": "等待Joy报价", "en": "Awaiting Joy Quotation"},
    "awaiting_ops_inquiry": {"zh": "等待运营询价", "en": "Awaiting Ops Inquiry"},
    "inquiry_succeeded": {"zh": "询价成功", "en": "Inquiry Succeeded"},
    "inquiry_failed": {"zh": "询价失败", "en": "Inquiry Failed"},
    "awaiting_ops_review": {"zh": "等待运营审核", "en": "Awaiting Ops Review"},
    "awaiting_customer_confirm": {"zh": "等待客户确认", "en": "Awaiting Customer Confirm"},
    "customer_confirmed_group": {"zh": "客户确认成团", "en": "Customer Confirmed Group"},
    "customer_confirm_failed": {"zh": "客户确认失败", "en": "Customer Confirm Failed"},
    "awaiting_hotel_lock": {"zh": "等待酒店锁房", "en": "Awaiting Hotel Room Lock"},
    "considering_alternative": {"zh": "考虑备选酒店", "en": "Considering Alternative Hotel"},
    "awaiting_payment": {"zh": "等待客户支付", "en": "Awaiting Payment"},
    "group_booking_success": {"zh": "团房成功", "en": "Group Booking Success"},
    "group_booking_failed": {"zh": "团房失败", "en": "Group Booking Failed"}
}

WORKFLOW_STEPS_ZH = [
    "customer_inquiry",
    "awaiting_joy_quotation",
    "awaiting_ops_inquiry",
    "inquiry_succeeded",
    "inquiry_failed",
    "awaiting_ops_review",
    "awaiting_customer_confirm",
    "customer_confirmed_group",
    "customer_confirm_failed",
    "awaiting_hotel_lock",
    "considering_alternative",
    "awaiting_payment",
    "group_booking_success",
    "group_booking_failed"
]

STATUS_FLOW_RULE = {
    "customer_inquiry": ["awaiting_joy_quotation", "awaiting_ops_inquiry"],
    "awaiting_joy_quotation": ["inquiry_succeeded", "inquiry_failed"],
    "awaiting_ops_inquiry": ["inquiry_succeeded", "inquiry_failed"],
    "inquiry_succeeded": ["awaiting_ops_review"],
    "inquiry_failed": [],
    "awaiting_ops_review": ["awaiting_customer_confirm"],
    "awaiting_customer_confirm": ["customer_confirmed_group", "customer_confirm_failed"],
    "customer_confirmed_group": ["awaiting_hotel_lock"],
    "customer_confirm_failed": [],
    "awaiting_hotel_lock": ["awaiting_payment", "considering_alternative", "group_booking_failed"],
    "considering_alternative": ["awaiting_hotel_lock"],
    "awaiting_payment": ["group_booking_success"],
    "group_booking_success": [],
    "group_booking_failed": []
}

def get_workflow_step_text(lang, status_key):
    if status_key not in STATUS_WORKFLOW_MAP:
        return status_key
    return STATUS_WORKFLOW_MAP[status_key][lang]

def get_standard_status(status_key):
    if status_key is None or (isinstance(status_key, float) and pd.isna(status_key)):
        return ""
    status_key = str(status_key).strip()
    if not status_key:
        return ""
    # 1. 直接是标准 key
    if status_key in STATUS_WORKFLOW_MAP:
        return status_key
    # 2. 精确匹配中/英文
    for key, mapping in STATUS_WORKFLOW_MAP.items():
        if mapping["zh"] == status_key or mapping["en"] == status_key:
            return key
    # 3. 处理 "中文 - English" 格式：按 " - " 拆分后精确匹配
    parts = [p.strip() for p in status_key.split(" - ")]
    if len(parts) == 2:
        zh_part, en_part = parts
        for key, mapping in STATUS_WORKFLOW_MAP.items():
            if mapping["zh"] == zh_part or mapping["en"] == en_part:
                return key
    # 4. 兜底：子串匹配（仅当标准名长度 >=3 时，避免误匹配）
    for key, mapping in STATUS_WORKFLOW_MAP.items():
        if len(mapping["zh"]) >= 3 and mapping["zh"] in status_key:
            return key
        if len(mapping["en"]) >= 3 and mapping["en"] in status_key:
            return key
    return status_key


STATUS_DURATION_COL_MAP = {
    "customer_inquiry": "客户咨询天数",
    "awaiting_joy_quotation": "等待Joy报价天数",
    "awaiting_ops_inquiry": "等待运营询价天数",
    "inquiry_succeeded": "询价成功天数",
    "inquiry_failed": "询价失败天数",
    "awaiting_ops_review": "等待运营审核天数",
    "awaiting_customer_confirm": "等待客户确认天数",
    "customer_confirmed_group": "客户确认成团天数",
    "customer_confirm_failed": "客户确认失败天数",
    "awaiting_hotel_lock": "等待酒店锁房天数",
    "considering_alternative": "考虑备选酒店天数",
    "awaiting_payment": "等待客户支付天数",
    "group_booking_success": "团房成功天数",
    "group_booking_failed": "团房失败天数"
}


def get_status_duration_col(status_key):
    """获取状态对应的持续天数列名"""
    std_status = get_standard_status(status_key)
    return STATUS_DURATION_COL_MAP.get(std_status, "")

# ---------------- 本地数据读写 ----------------
def init_csv():
    if not os.path.exists(DATA_FILE):
        cols = [
            "团单号", "客户名称 Customer Name", "User ID", "国籍 Nationality",
            "房间总数 Total Rooms", "状态", "提交时间 Submitted by", "最后更新时间", "国家 Country",
            "联系方式 Contact Info", "入住日期 Check-in Date", "离店日期 Check-out Date",
            "房型要求 Room Type", "报价币种 Currency", "预算范围 Budget Range",
            "房间数 Rooms", "酒店星级 Star Rating", "间夜数 Room Nights",
            "会议室/交通需求 Meeting Room / Transportation Requirements",
            "出行目的 Purpose of travel", "特殊需求 Special Requests",
            "Joy 底价 Joy's Net Rate", "建议卖价 Suggested Selling Price",
            "额外税费需求 Extra tax if needed", "房间保留时间", "支付方式",
            "餐食", "取消政策", "未成单原因（一级）", "未成单原因（二级）", "运营备注 Ops Notes", "BD", "Salesteam", "酒店名称 Hotel Name",
            "销售姓名 Sales Name", "Channel OP", "备注",
            "上次状态变更时间",
            "客户咨询天数", "等待Joy报价天数", "等待运营询价天数", "询价成功天数", "询价失败天数",
            "等待运营审核天数", "等待客户确认天数", "客户确认成团天数", "客户确认失败天数",
            "等待酒店锁房天数", "考虑备选酒店天数", "等待客户支付天数", "团房成功天数", "团房失败天数"
        ]
        df = pd.DataFrame(columns=cols)
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def load_data():
    init_csv()
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig", dtype=str)
    df = df.fillna("")
    
    expected_cols = [
        "团单号", "客户名称 Customer Name", "User ID", "国籍 Nationality",
        "房间总数 Total Rooms", "状态", "提交时间 Submitted by", "最后更新时间", "国家 Country",
        "联系方式 Contact Info", "入住日期 Check-in Date", "离店日期 Check-out Date",
        "房型要求 Room Type", "报价币种 Currency", "预算范围 Budget Range",
        "房间数 Rooms", "酒店星级 Star Rating", "间夜数 Room Nights",
        "会议室/交通需求 Meeting Room / Transportation Requirements",
        "出行目的 Purpose of travel", "特殊需求 Special Requests",
        "Joy 底价 Joy's Net Rate", "建议卖价 Suggested Selling Price",
        "额外税费需求 Extra tax if needed", "房间保留时间", "支付方式",
        "餐食", "取消政策", "未成单原因（一级）", "未成单原因（二级）", "运营备注 Ops Notes", "BD", "Salesteam", "酒店名称 Hotel Name",
        "销售姓名 Sales Name", "Channel OP", "备注",
        "上次状态变更时间",
        "客户咨询天数", "等待Joy报价天数", "等待运营询价天数", "询价成功天数", "询价失败天数",
        "等待运营审核天数", "等待客户确认天数", "客户确认成团天数", "客户确认失败天数",
        "等待酒店锁房天数", "考虑备选酒店天数", "等待客户支付天数", "团房成功天数", "团房失败天数"
    ]
    
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    
    return df[expected_cols]

def save_data(df):
    # 确保所有预期的列都存在
    expected_cols = [
        "团单号", "客户名称 Customer Name", "User ID", "国籍 Nationality",
        "房间总数 Total Rooms", "状态", "提交时间 Submitted by", "最后更新时间", "国家 Country",
        "联系方式 Contact Info", "入住日期 Check-in Date", "离店日期 Check-out Date",
        "房型要求 Room Type", "报价币种 Currency", "预算范围 Budget Range",
        "房间数 Rooms", "酒店星级 Star Rating", "间夜数 Room Nights",
        "会议室/交通需求 Meeting Room / Transportation Requirements",
        "出行目的 Purpose of travel", "特殊需求 Special Requests",
        "Joy 底价 Joy's Net Rate", "建议卖价 Suggested Selling Price",
        "额外税费需求 Extra tax if needed", "房间保留时间", "支付方式",
        "餐食", "取消政策", "未成单原因（一级）", "未成单原因（二级）", "运营备注 Ops Notes", "BD", "Salesteam", "酒店名称 Hotel Name",
        "销售姓名 Sales Name", "Channel OP", "备注",
        "上次状态变更时间",
        "客户咨询天数", "等待Joy报价天数", "等待运营询价天数", "询价成功天数", "询价失败天数",
        "等待运营审核天数", "等待客户确认天数", "客户确认成团天数", "客户确认失败天数",
        "等待酒店锁房天数", "考虑备选酒店天数", "等待客户支付天数", "团房成功天数", "团房失败天数"
    ]
    
    # 添加缺失的列
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    
    # 按照预期顺序保存
    df = df[expected_cols]
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

# ---------------- 飞书API工具（使用电子表格Spreadsheet API） ----------------
def get_tenant_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": app_id.strip(),
        "app_secret": app_secret.strip()
    }
    headers = {"Content-Type": "application/json; charset=utf-8"}
    resp = requests.post(url, json=payload, headers=headers, timeout=12)
    res = resp.json()
    if res.get("code") != 0:
        raise Exception(f"Tenant Access Token获取失败:{res}")
    return res["tenant_access_token"]

def load_feishu_config():
    config_path = "feishu_config.json"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def fetch_feishu_table():
    return _fetch_feishu_sheet("sheet_id", "sheet_id")


def fetch_feishu_price_table():
    """获取飞书比价数据表格（使用 price_sheet_id 配置）"""
    return _fetch_feishu_sheet("price_sheet_id", "price_sheet_id")


def write_feishu_price_table(df):
    """写入飞书比价数据表格"""
    return _write_feishu_sheet(df, "price_sheet_id", "price_sheet_id")


def _fetch_feishu_sheet(config_key, label):
    """通用飞书表格读取函数"""
    config = load_feishu_config()

    try:
        import streamlit as st
        st_secrets = st.secrets
    except:
        st_secrets = {}

    app_id = os.environ.get("FEISHU_APP_ID") or st_secrets.get("FEISHU_APP_ID", "") or config.get("app_id", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET") or st_secrets.get("FEISHU_APP_SECRET", "") or config.get("app_secret", "")
    spreadsheet_token = os.environ.get("FEISHU_SPREADSHEET_TOKEN") or st_secrets.get("FEISHU_SPREADSHEET_TOKEN", "") or config.get("spreadsheet_token", "")
    sheet_id = os.environ.get(f"FEISHU_{label.upper()}") or st_secrets.get(f"FEISHU_{label.upper()}", "") or config.get(config_key, "")

    if not app_id or not app_secret:
        raise Exception("未配置飞书app_id或app_secret！请在Streamlit Secrets或feishu_config.json中配置")
    if not sheet_id:
        raise Exception(f"未配置{config_key}！请在Streamlit Secrets或feishu_config.json中添加{config_key}字段")

    try:
        token = get_tenant_token(app_id, app_secret)
        print(f"[飞书同步] Tenant Access Token获取成功，token长度: {len(token)}")
    except Exception as e:
        print(f"[飞书同步] Token获取失败: {str(e)}")
        raise

    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values/{sheet_id}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=12)
    res = resp.json()
    print(f"[飞书同步] 读取表格API响应: {json.dumps(res, ensure_ascii=False)}")

    if res.get("code") != 0:
        if res.get("code") == 90215:
            raise Exception(f"错误码90215: 未找到sheetId！请确认feishu_config.json中的{config_key}是否正确")
        if res.get("code") == 99991672:
            raise Exception(f"错误码99991672: 需要开通飞书权限！请访问以下链接开通权限：\nhttps://open.feishu.cn/app/{app_id}/auth?q=drive:file:readonly&op_from=openapi&token_type=tenant")
        raise Exception(f"读取表格失败:{res}")

    values = res["data"]["valueRange"]["values"]
    if not values:
        print("[飞书同步] 飞书表格无有效数据")
        return pd.DataFrame()

    headers = values[0]
    data_rows = values[1:] if len(values) > 1 else []

    # 处理列名中可能包含的链接对象
    processed_headers = []
    for h in headers:
        if isinstance(h, list):
            # 如果是列表（包含链接对象），提取文本
            for item in h:
                if isinstance(item, dict) and 'text' in item:
                    processed_headers.append(item['text'])
                    break
            else:
                processed_headers.append(str(h))
        elif isinstance(h, dict) and 'text' in h:
            # 如果是链接对象
            processed_headers.append(h['text'])
        else:
            processed_headers.append(str(h))

    df = pd.DataFrame(data_rows, columns=processed_headers)

    # 去重列名：保留第一个，移除重复列（使用索引移除，避免df.drop移除所有同名列）
    seen = set()
    duplicate_cols = []
    for i, col in enumerate(df.columns):
        if col in seen:
            duplicate_cols.append(i)
        else:
            seen.add(col)
    if duplicate_cols:
        print(f"[飞书同步] 发现重复列，将移除索引 {duplicate_cols}: {[df.columns[i] for i in duplicate_cols]}")
        keep_cols = [i for i in range(len(df.columns)) if i not in duplicate_cols]
        df = df.iloc[:, keep_cols]

    # 关键修复：创建新DataFrame存储处理后的数据，避免类型不匹配问题
    # 当原DataFrame某列是int64/float64类型时，直接赋值字符串Series会失败
    new_df = pd.DataFrame()
    for i, col in enumerate(df.columns):
        # 先解析飞书单元格内容
        processed_col = df.iloc[:, i].apply(lambda x: _parse_feishu_cell(x))
        # 先fillna("")填充所有NaN值，再astype(str)转换为字符串
        processed_col = processed_col.fillna("").astype(str).str.strip().str.replace(r"[\n\r]", "", regex=True)
        # 使用列名赋值到新DataFrame，避免iloc类型检查问题
        new_df[col] = processed_col

    new_df = new_df.replace(["nan", "None", "[]", "null"], "")

    print(f"[飞书同步] 成功读取 {len(new_df)} 条数据，列名: {list(new_df.columns)}")
    return new_df

def _parse_feishu_cell(value):
    if isinstance(value, list):
        text_parts = []
        for item in value:
            if isinstance(item, dict):
                text = item.get("text", "")
                if text:
                    text_parts.append(text)
            else:
                text_parts.append(str(item))
        return "".join(text_parts)
    return str(value)


def _col_num_to_letter(n):
    """将列号转换为Excel列字母（1->A, 26->Z, 27->AA）"""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result

def _write_feishu_sheet(df, config_key, label):
    """通用飞书表格写入函数"""
    config = load_feishu_config()

    try:
        import streamlit as st
        st_secrets = st.secrets
    except:
        st_secrets = {}

    app_id = os.environ.get("FEISHU_APP_ID") or st_secrets.get("FEISHU_APP_ID", "") or config.get("app_id", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET") or st_secrets.get("FEISHU_APP_SECRET", "") or config.get("app_secret", "")
    spreadsheet_token = os.environ.get("FEISHU_SPREADSHEET_TOKEN") or st_secrets.get("FEISHU_SPREADSHEET_TOKEN", "") or config.get("spreadsheet_token", "")
    sheet_id = os.environ.get(f"FEISHU_{label.upper()}") or st_secrets.get(f"FEISHU_{label.upper()}", "") or config.get(config_key, "")

    print(f"[飞书写入] 配置检查 - app_id: {repr(app_id[:10]) if app_id else '空'}, app_secret: {'有' if app_secret else '空'}, spreadsheet_token: {repr(spreadsheet_token[:10]) if spreadsheet_token else '空'}, sheet_id: {repr(sheet_id)}")

    if not app_id or not app_secret:
        raise Exception("未配置飞书app_id或app_secret！请在Streamlit Secrets或feishu_config.json中配置")
    if not sheet_id:
        raise Exception(f"未配置{config_key}！请在Streamlit Secrets或feishu_config.json中添加{config_key}字段")

    try:
        token = get_tenant_token(app_id, app_secret)
        print(f"[飞书写入] Tenant Access Token获取成功，token长度: {len(token)}")
    except Exception as e:
        print(f"[飞书写入] Token获取失败: {str(e)}")
        raise

    url = f"https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/{spreadsheet_token}/values"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    values = [list(df.columns)] + df.fillna("").values.tolist()
    
    print(f"[飞书写入] 准备写入{len(values)-1}条数据，列名: {list(df.columns)}")
    print(f"[飞书写入] 数据预览(前2行): {values[:2]}")

    col_letter = _col_num_to_letter(len(df.columns))
    
    max_rows = 2000
    clear_range = f"{sheet_id}!A1:{col_letter}{max_rows}"
    clear_body = {
        "valueRange": {
            "range": clear_range,
            "values": [[""] * len(df.columns)] * max_rows
        },
        "valueInputOption": "USER_ENTERED"
    }
    try:
        clear_resp = requests.put(url, headers=headers, json=clear_body, timeout=12)
        clear_res = clear_resp.json()
        print(f"[飞书写入] 清空表格响应: {json.dumps(clear_res, ensure_ascii=False)}")
    except Exception as clear_err:
        print(f"[飞书写入] 清空表格失败（继续写入）: {str(clear_err)}")

    body = {
        "valueRange": {
            "range": f"{sheet_id}!A1:{col_letter}{len(values)}",
            "values": values
        },
        "valueInputOption": "USER_ENTERED"
    }

    print(f"[飞书写入] 请求URL: {url}")
    print(f"[飞书写入] 请求体: {json.dumps(body, ensure_ascii=False)[:500]}...")
    
    resp = requests.put(url, headers=headers, json=body, timeout=12)
    res = resp.json()
    print(f"[飞书写入] HTTP状态码: {resp.status_code}")
    print(f"[飞书写入] 写入表格API响应: {json.dumps(res, ensure_ascii=False)}")
    print(f"[飞书写入] code类型: {type(res.get('code'))}, code值: {repr(res.get('code'))}")

    code = res.get("code")
    if code is not None and str(code) != "0":
        raise Exception(f"写入表格失败:{res}")

    print(f"[飞书写入] 成功写入 {len(df)} 条数据")
    return True

def configure_matplotlib_font():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import os
    
    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    os.makedirs(font_dir, exist_ok=True)
    
    font_path = os.path.join(font_dir, "NotoSansCJKsc-Regular.otf")
    
    if not os.path.exists(font_path):
        try:
            import urllib.request
            import zipfile
            import io
            url = "https://github.com/notofonts/noto-cjk/releases/download/Sans2.004/08_NotoSansCJKsc.zip"
            response = urllib.request.urlopen(url)
            zip_data = response.read()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                for name in zf.namelist():
                    if "Regular" in name:
                        zf.extract(name, font_dir)
                        os.rename(os.path.join(font_dir, name), font_path)
                        break
            print("[字体配置] 字体下载完成")
        except Exception as e:
            print(f"[字体配置] 字体下载失败: {e}")
    
    if os.path.exists(font_path):
        try:
            font_prop = fm.FontProperties(fname=font_path)
            fm.fontManager.addfont(font_path)
            plt.rcParams["font.family"] = font_prop.get_name()
            plt.rcParams["font.sans-serif"] = [font_prop.get_name()]
            plt.rcParams["axes.unicode_minus"] = False
            print(f"[字体配置] 使用本地下载字体: {font_prop.get_name()}")
            return
        except Exception as e:
            print(f"[字体配置] 本地字体加载失败: {e}")
    
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    available_fonts_lower = [f.lower() for f in available_fonts]
    
    chinese_fonts = [
        "SimHei", "Microsoft YaHei", "Microsoft YaHei UI",
        "Noto Sans SC", "Noto Sans CJK SC", "Noto Sans CJK",
        "Arial Unicode MS", "WenQuanYi Micro Hei",
        "Heiti SC", "Heiti TC", "STSong", "STHeiti",
        "DejaVu Sans"
    ]
    
    selected_font = None
    for font in chinese_fonts:
        if font.lower() in available_fonts_lower:
            idx = available_fonts_lower.index(font.lower())
            selected_font = available_fonts[idx]
            break
    
    if selected_font:
        plt.rcParams["font.family"] = selected_font
        plt.rcParams["font.sans-serif"] = [selected_font]
        plt.rcParams["axes.unicode_minus"] = False
        print(f"[字体配置] 使用系统字体: {selected_font}")
    else:
        plt.rcParams["font.family"] = ["DejaVu Sans"]
        plt.rcParams["font.sans-serif"] = ["DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
        print(f"[字体配置] 未找到中文字体，使用默认: DejaVu Sans")
        print(f"[字体配置] 可用字体列表: {available_fonts[:20]}")