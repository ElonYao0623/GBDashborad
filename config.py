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
    if status_key in STATUS_WORKFLOW_MAP:
        return status_key
    for key, mapping in STATUS_WORKFLOW_MAP.items():
        if mapping["zh"] == status_key or mapping["en"] == status_key:
            return key
        if mapping["zh"] in status_key or mapping["en"] in status_key:
            return key
    return status_key

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
            "餐食", "取消政策", "未成单原因", "运营备注 Ops Notes", "BD", "Salesteam", "酒店名称 Hotel Name",
            "销售姓名 Sales Name", "备注"
        ]
        df = pd.DataFrame(columns=cols)
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def load_data():
    init_csv()
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig", dtype=str)
    df = df.fillna("")
    return df

def save_data(df):
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
    config = load_feishu_config()
    
    try:
        import streamlit as st
        st_secrets = st.secrets
    except:
        st_secrets = {}
    
    app_id = os.environ.get("FEISHU_APP_ID") or st_secrets.get("FEISHU_APP_ID", "") or config.get("app_id", "")
    app_secret = os.environ.get("FEISHU_APP_SECRET") or st_secrets.get("FEISHU_APP_SECRET", "") or config.get("app_secret", "")
    spreadsheet_token = os.environ.get("FEISHU_SPREADSHEET_TOKEN") or st_secrets.get("FEISHU_SPREADSHEET_TOKEN", "") or config.get("spreadsheet_token", "")
    sheet_id = os.environ.get("FEISHU_SHEET_ID") or st_secrets.get("FEISHU_SHEET_ID", "") or config.get("sheet_id", "")

    if not app_id or not app_secret:
        raise Exception("未配置飞书app_id或app_secret！请在Streamlit Secrets或feishu_config.json中配置")
    if not sheet_id:
        raise Exception("未配置sheet_id！请在Streamlit Secrets或feishu_config.json中添加sheet_id字段")

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
            raise Exception(f"错误码90215: 未找到sheetId！请确认feishu_config.json中的sheet_id是否正确")
        if res.get("code") == 99991672:
            raise Exception(f"错误码99991672: 需要开通飞书权限！请访问以下链接开通权限：\nhttps://open.feishu.cn/app/{app_id}/auth?q=drive:file:readonly&op_from=openapi&token_type=tenant")
        raise Exception(f"读取表格失败:{res}")

    values = res["data"]["valueRange"]["values"]
    if not values:
        print("[飞书同步] 飞书表格无有效数据")
        return pd.DataFrame()

    headers = values[0]
    data_rows = values[1:] if len(values) > 1 else []
    
    df = pd.DataFrame(data_rows, columns=headers)

    for col in df.columns:
        df[col] = df[col].apply(lambda x: _parse_feishu_cell(x))
        df[col] = df[col].str.strip().str.replace(r"[\n\r]", "", regex=True)
    
    df = df.replace(["nan", "None", "[]"], "")
    
    print(f"[飞书同步] 成功读取 {len(df)} 条数据，列名: {list(df.columns)}")
    return df

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

def configure_matplotlib_font():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    import os
    
    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    os.makedirs(font_dir, exist_ok=True)
    
    font_path = os.path.join(font_dir, "NotoSansCJK-SC.otf")
    
    if not os.path.exists(font_path):
        try:
            import urllib.request
            url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/SimplifiedChinese/NotoSansCJK-SC-Regular.otf"
            urllib.request.urlretrieve(url, font_path)
        except:
            pass
    
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
        "Arial Unicode MS", "WenQuanYi Zen Hei",
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
