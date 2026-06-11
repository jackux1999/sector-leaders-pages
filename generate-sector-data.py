#!/usr/bin/env python3
import json
import math
import sys
import urllib.request
from datetime import datetime
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_FILE = ROOT / "data" / "sectors-data.js"
VENDOR = ROOT / "vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))

EXCLUDED_PREFIXES = ("300", "301", "688")
TOP_INDUSTRY_COUNT = 5
TOP_STOCK_COUNT = 5


SECTOR_CONFIG = [
    {
        "id": "mlcc",
        "name": "MLCC",
        "aliases": ["MLCC", "被动元件", "电子元件"],
        "stocks": ["000636", "002859", "002138", "603678", "605218", "002484", "600563", "002463", "002436", "603738"],
        "industry": ["风华高科", "洁美科技", "顺络电子"],
        "summary": "按板块成份股涨幅、成交额、换手率和涨停状态生成交易龙头，适合盘后观察资金强度。",
    },
    {
        "id": "lithium",
        "name": "锂电",
        "aliases": ["锂电池", "动力电池回收", "固态电池"],
        "stocks": ["002709", "002460", "002812", "002466", "002074", "002340", "002176", "600884", "603659", "603799", "002756", "002594"],
        "industry": ["天赐材料", "赣锋锂业", "恩捷股份"],
        "summary": "锂电板块重点观察权重龙头和材料弹性股是否共振。",
    },
    {
        "id": "robot",
        "name": "机器人",
        "aliases": ["机器人概念", "人形机器人", "机器视觉"],
        "stocks": ["002896", "002747", "603728", "002527", "002031", "603662", "603960", "002472", "002559", "603666", "603015"],
        "industry": ["中大力德", "埃斯顿", "鸣志电器"],
        "summary": "机器人板块短线看涨停辨识度，中线看减速器、控制器和执行器等核心环节。",
    },
    {
        "id": "cpo",
        "name": "CPO",
        "aliases": ["CPO概念", "光通信模块", "F5G概念"],
        "stocks": ["000988", "002281", "600522", "600487", "000063", "002463", "002929", "600498", "002396", "002902"],
        "industry": ["华工科技", "光迅科技", "中天科技"],
        "summary": "CPO板块主要跟随 AI 算力链景气度，成交额龙头通常决定板块持续性。",
    },
    {
        "id": "chip",
        "name": "半导体",
        "aliases": ["半导体", "芯片概念", "第三代半导体"],
        "stocks": ["002371", "603986", "002156", "603501", "002049", "600584", "600460", "002185", "600703", "002409", "605358"],
        "industry": ["北方华创", "兆易创新", "通富微电"],
        "summary": "半导体板块容量大，设备、材料、存储和先进封装经常轮动。",
    },
    {
        "id": "solid",
        "name": "固态电池",
        "aliases": ["固态电池", "钠离子电池", "锂电池"],
        "stocks": ["603200", "002460", "002709", "002812", "002074", "002466", "002340", "002176", "600884", "603799"],
        "industry": ["赣锋锂业", "天赐材料", "恩捷股份"],
        "summary": "固态电池主题弹性强，适合观察日内领涨股和产业链容量股是否同步走强。",
    },
]


def clean_number(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return default
        return float(value)
    text = str(value).replace(",", "").replace("%", "").replace("亿", "").replace("万", "").strip()
    if text in {"", "-", "None", "nan"}:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def get_value(row, names, default=None):
    for name in names:
        if name in row:
            return row[name]
    return default


def normalize_amount(value):
    text = str(value)
    if "亿" in text:
        return round(clean_number(text), 2)
    if "万" in text:
        return round(clean_number(text) / 10000, 2)
    amount = clean_number(value)
    if amount > 100000000:
        return round(amount / 100000000, 2)
    if amount > 10000:
        return round(amount / 10000, 2)
    return round(amount, 2)


def is_limit_up(code, change):
    code = str(code)
    return change >= 9.8


def is_allowed_code(code):
    return not str(code).zfill(6).startswith(EXCLUDED_PREFIXES)


def score(stock):
    clipped_change = max(-10, min(stock["change"], 10))
    change_score = ((clipped_change + 10) / 20) * 55
    amount_score = min(stock["amount"] / 80, 1) * 30
    turnover_score = min(stock["turnover"] / 15, 1) * 10
    limit_score = 5 if stock["limit"] else 0
    return round(change_score + amount_score + turnover_score + limit_score)


def board_heat(row):
    change = clean_number(get_value(row, ["涨跌幅", "涨跌幅%"], 0))
    amount = normalize_amount(get_value(row, ["成交额", "成交金额", "总成交额"], 0))
    turnover = clean_number(get_value(row, ["换手率", "换手率%"], 0))
    leader_change = clean_number(get_value(row, ["领涨股票-涨跌幅", "领涨股涨跌幅", "领涨涨幅"], 0))
    up_count = clean_number(get_value(row, ["上涨家数", "上涨数"], 0))
    down_count = clean_number(get_value(row, ["下跌家数", "下跌数"], 0))
    breadth = up_count / max(up_count + down_count, 1)

    change_score = ((max(-5, min(change, 10)) + 5) / 15) * 45
    amount_score = min(amount / 300, 1) * 30
    turnover_score = min(turnover / 8, 1) * 10
    leader_score = ((max(-5, min(leader_change, 10)) + 5) / 15) * 10
    breadth_score = breadth * 5
    return round(change_score + amount_score + turnover_score + leader_score + breadth_score)


def industry_score(stock, industry_names):
    if stock["name"] in industry_names:
        return max(86, 98 - industry_names.index(stock["name"]) * 4)
    return min(84, max(60, score(stock) + 10))


def reason_for(stock, sector_name):
    if stock["limit"]:
        return f"{sector_name}板块内涨停，涨幅和换手率同步靠前，短线辨识度较高。"
    if stock["amount"] >= 50:
        return f"{sector_name}板块内成交额居前，容量较大，是观察板块强弱的重要锚点。"
    if stock["turnover"] >= 8:
        return f"{sector_name}板块内换手充分，交易活跃度高，适合观察资金接力。"
    return f"{sector_name}板块内综合强度靠前，涨幅、成交额和换手率表现相对均衡。"


def load_akshare():
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("未安装 akshare，请先运行：python3 -m pip install akshare") from exc
    return ak


def find_board_symbol(boards, aliases):
    name_col = "板块名称"
    if name_col not in boards.columns:
        return None
    names = boards[name_col].astype(str).tolist()
    for alias in aliases:
        for name in names:
            if name == alias:
                return name
        for name in names:
            if alias in name or name in alias:
                return name
    return None


def board_amount(boards, symbol):
    if symbol is None or "板块名称" not in boards.columns:
        return 0.0
    rows = boards[boards["板块名称"].astype(str) == symbol]
    if rows.empty:
        return 0.0
    row = rows.iloc[0].to_dict()
    return normalize_amount(get_value(row, ["成交额", "成交金额", "总成交额"], 0))


def board_change(boards, symbol):
    if symbol is None or "板块名称" not in boards.columns:
        return 0.0
    rows = boards[boards["板块名称"].astype(str) == symbol]
    if rows.empty:
        return 0.0
    row = rows.iloc[0].to_dict()
    return round(clean_number(get_value(row, ["涨跌幅", "涨跌幅%"], 0)), 2)


def board_leader_names(row):
    names = []
    for key in ["领涨股票", "领涨股", "领涨名称"]:
        value = get_value(row, [key], "")
        if value:
            names.append(str(value))
    return names


def build_stock(row, sector_name, industry_names):
    code = str(get_value(row, ["代码", "股票代码"], "")).zfill(6)
    if not is_allowed_code(code):
        return None
    name = str(get_value(row, ["名称", "股票名称"], ""))
    change = round(clean_number(get_value(row, ["涨跌幅", "涨跌幅%", "涨跌幅(%)"], 0)), 2)
    amount = normalize_amount(get_value(row, ["成交额", "成交金额"], 0))
    turnover = round(clean_number(get_value(row, ["换手率", "换手率%", "换手(%)"], 0)), 2)
    stock = {
        "name": name,
        "code": code,
        "change": change,
        "amount": amount,
        "turnover": turnover,
        "limit": is_limit_up(code, change),
    }
    stock["reason"] = reason_for(stock, sector_name)
    stock["industryScore"] = industry_score(stock, industry_names)
    return stock


def build_ths_stock(row, sector_name, industry_names):
    code = str(get_value(row, ["代码", "股票代码"], "")).strip().zfill(6)
    if not is_allowed_code(code):
        return None
    stock = {
        "name": str(get_value(row, ["名称", "股票简称", "股票名称"], "")),
        "code": code,
        "change": round(clean_number(get_value(row, ["涨跌幅(%)", "涨跌幅", "涨跌幅%"], 0)), 2),
        "amount": normalize_amount(get_value(row, ["成交额", "成交金额"], 0)),
        "turnover": round(clean_number(get_value(row, ["换手(%)", "换手率", "换手率%"], 0)), 2),
        "limit": False,
    }
    stock["limit"] = is_limit_up(code, stock["change"])
    stock["reason"] = reason_for(stock, sector_name)
    stock["industryScore"] = industry_score(stock, industry_names)
    return stock


def build_industry_sector(ak, boards, board_row, index):
    symbol = str(get_value(board_row, ["板块名称", "行业名称"], "")).strip()
    if not symbol:
        raise RuntimeError("行业名称为空")

    cons = ak.stock_board_industry_cons_em(symbol=symbol)
    preferred_names = board_leader_names(board_row)
    stocks = [
        build_stock(row, symbol, preferred_names)
        for row in cons.to_dict("records")
    ]
    stocks = [stock for stock in stocks if stock and stock["name"] and stock["code"]]
    stocks.sort(key=score, reverse=True)
    leaders = stocks[:TOP_STOCK_COUNT]
    industry = [name for name in preferred_names if any(stock["name"] == name for stock in leaders)]
    industry += [stock["name"] for stock in leaders if stock["name"] not in industry]

    return {
        "id": f"industry-{index + 1}",
        "name": symbol,
        "change": round(clean_number(get_value(board_row, ["涨跌幅", "涨跌幅%"], 0)), 2),
        "amount": board_amount(boards, symbol) or round(sum(stock["amount"] for stock in stocks), 1),
        "heat": board_heat(board_row),
        "summary": f"东方财富行业热度前 {TOP_INDUSTRY_COUNT}，按行业成份股涨幅、成交额、换手率和涨停状态筛选前 {TOP_STOCK_COUNT} 只股票。 数据板块源：{symbol}。",
        "trading": leaders,
        "industry": industry[:TOP_STOCK_COUNT],
    }


def ths_headers():
    import py_mini_racer
    from akshare.datasets import get_ths_js

    js_code = py_mini_racer.MiniRacer()
    with open(get_ths_js("ths.js"), encoding="utf-8") as file:
        js_code.eval(file.read())
    v_code = js_code.call("v")
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Cookie": f"v={v_code}",
        "hexin-v": v_code,
        "Referer": "http://q.10jqka.com.cn/thshy/",
    }


def ths_industry_codes(ak):
    frame = ak.stock_board_industry_name_ths()
    return {
        str(row["name"]): str(row["code"])
        for row in frame.to_dict("records")
        if row.get("name") and row.get("code")
    }


def fetch_ths_industry_stocks(code, headers, max_pages=10):
    import pandas as pd
    import requests

    records = []
    seen = set()
    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"http://q.10jqka.com.cn/thshy/detail/code/{code}/"
        else:
            url = f"http://q.10jqka.com.cn/thshy/detail/code/{code}/field/199112/order/desc/page/{page}/"
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        tables = pd.read_html(StringIO(response.text))
        if not tables:
            break
        page_records = tables[0].to_dict("records")
        new_records = []
        for row in page_records:
            stock_code = str(get_value(row, ["代码", "股票代码"], "")).strip().zfill(6)
            if not stock_code or stock_code in seen:
                continue
            seen.add(stock_code)
            new_records.append(row)
        records.extend(new_records)
        allowed_count = sum(1 for row in records if is_allowed_code(get_value(row, ["代码", "股票代码"], "")))
        if allowed_count >= TOP_STOCK_COUNT or not new_records:
            break
    return records


def build_ths_sector(ak, code_map, headers, board_row, index):
    symbol = str(get_value(board_row, ["板块", "板块名称", "行业名称"], "")).strip()
    if not symbol:
        raise RuntimeError("行业名称为空")
    code = code_map.get(symbol)
    if not code:
        raise RuntimeError(f"找不到同花顺行业代码：{symbol}")

    preferred_names = board_leader_names(board_row)
    stocks = [
        build_ths_stock(row, symbol, preferred_names)
        for row in fetch_ths_industry_stocks(code, headers)
    ]
    stocks = [stock for stock in stocks if stock and stock["name"] and stock["code"]]
    stocks.sort(key=score, reverse=True)
    leaders = stocks[:TOP_STOCK_COUNT]
    industry = [name for name in preferred_names if any(stock["name"] == name for stock in leaders)]
    industry += [stock["name"] for stock in leaders if stock["name"] not in industry]

    return {
        "id": f"industry-{index + 1}",
        "name": symbol,
        "change": round(clean_number(get_value(board_row, ["涨跌幅", "涨跌幅%"], 0)), 2),
        "amount": normalize_amount(get_value(board_row, ["总成交额", "成交额", "成交金额"], 0)),
        "heat": board_heat(board_row),
        "summary": f"同花顺行业热度前 {TOP_INDUSTRY_COUNT}，按行业成份股涨幅、成交额、换手率和涨停状态筛选前 {TOP_STOCK_COUNT} 只股票。 数据板块源：{symbol}。",
        "trading": leaders,
        "industry": industry[:TOP_STOCK_COUNT],
    }


def build_sector(ak, boards, config):
    symbol = find_board_symbol(boards, config["aliases"])
    if not symbol:
        raise RuntimeError(f"找不到板块：{config['name']}")

    cons = ak.stock_board_concept_cons_em(symbol=symbol)
    stocks = [
        build_stock(row, config["name"], config["industry"])
        for row in cons.to_dict("records")
    ]
    stocks = [stock for stock in stocks if stock and stock["name"] and stock["code"]]
    stocks.sort(key=score, reverse=True)
    leaders = stocks[:TOP_STOCK_COUNT]
    industry = [name for name in config["industry"] if any(stock["name"] == name for stock in leaders)]
    industry += [stock["name"] for stock in leaders if stock["name"] not in industry]

    return {
        "id": config["id"],
        "name": config["name"],
        "change": board_change(boards, symbol),
        "amount": round(sum(stock["amount"] for stock in stocks), 1),
        "heat": min(100, max(0, round(sum(score(stock) for stock in leaders) / max(len(leaders), 1)))),
        "summary": config["summary"] + f" 数据板块源：{symbol}。",
        "trading": leaders,
        "industry": industry[:TOP_STOCK_COUNT],
    }


def market_code(code):
    code = str(code).zfill(6)
    if code.startswith(("6", "9")):
        return f"sh{code}"
    return f"sz{code}"


def fetch_sina_quotes(codes):
    codes = [str(code).zfill(6) for code in codes if is_allowed_code(code)]
    symbols = ",".join(market_code(code) for code in codes)
    url = f"https://hq.sinajs.cn/list={symbols}"
    req = urllib.request.Request(
        url,
        headers={
            "Referer": "https://finance.sina.com.cn/",
            "User-Agent": "Mozilla/5.0",
        },
    )
    raw = urllib.request.urlopen(req, timeout=15).read().decode("gbk", errors="ignore")
    quotes = {}
    for line in raw.splitlines():
        if not line.startswith("var hq_str_"):
            continue
        left, right = line.split("=", 1)
        symbol = left.replace("var hq_str_", "").strip()
        code = symbol[-6:]
        if not is_allowed_code(code):
            continue
        values = right.strip().strip('";').split(",")
        if len(values) < 32 or not values[0]:
            continue
        prev_close = clean_number(values[2])
        current = clean_number(values[3])
        if current <= 0 or prev_close <= 0:
            continue
        change = round((current - prev_close) / prev_close * 100, 2)
        quotes[code] = {
            "name": values[0],
            "code": code,
            "change": change,
            "amount": round(clean_number(values[9]) / 100000000, 2),
            "turnover": 0.0,
            "limit": is_limit_up(code, change),
            "date": values[30] if len(values) > 30 else "",
            "time": values[31] if len(values) > 31 else "",
        }
    return quotes


def build_sina_sector(config, quotes):
    stocks = []
    for code in config["stocks"]:
        stock = quotes.get(str(code).zfill(6))
        if not stock:
            continue
        stock = dict(stock)
        stock["reason"] = reason_for(stock, config["name"])
        stock["industryScore"] = industry_score(stock, config["industry"])
        stocks.append(stock)

    stocks.sort(key=score, reverse=True)
    leaders = stocks[:TOP_STOCK_COUNT]
    industry = [name for name in config["industry"] if any(stock["name"] == name for stock in leaders)]
    industry += [stock["name"] for stock in leaders if stock["name"] not in industry]

    avg_change = sum(stock["change"] for stock in stocks) / max(len(stocks), 1)
    return {
        "id": config["id"],
        "name": config["name"],
        "change": round(avg_change, 2),
        "amount": round(sum(stock["amount"] for stock in stocks), 1),
        "heat": min(100, max(0, round(sum(score(stock) for stock in leaders) / max(len(leaders), 1)))),
        "summary": config["summary"] + " 数据板块源：自维护股票池/新浪行情。",
        "trading": leaders,
        "industry": industry[:TOP_STOCK_COUNT],
    }


def generate_sina():
    all_codes = []
    for config in SECTOR_CONFIG:
        all_codes.extend(config["stocks"])
    quotes = fetch_sina_quotes(sorted(set(all_codes)))
    sectors = [build_sina_sector(config, quotes) for config in SECTOR_CONFIG]
    sectors = [sector for sector in sectors if sector["trading"]]
    if not sectors:
        raise RuntimeError("新浪行情没有返回有效股票数据")
    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "source": "新浪行情/自维护股票池",
        "errors": [],
        "sectors": sectors,
    }


def generate_akshare():
    ak = load_akshare()
    try:
        return generate_eastmoney_industries(ak)
    except Exception as eastmoney_error:
        payload = generate_ths_industries(ak)
        payload["errors"].insert(0, f"东方财富行业板块不可用，已切换同花顺行业：{eastmoney_error}")
        return payload


def generate_eastmoney_industries(ak):
    boards = ak.stock_board_industry_name_em()
    if "板块名称" not in boards.columns:
        raise RuntimeError(f"行业板块接口缺少板块名称字段：{list(boards.columns)}")

    sectors = []
    errors = []
    board_rows = sorted(boards.to_dict("records"), key=board_heat, reverse=True)
    for board_row in board_rows:
        if len(sectors) >= TOP_INDUSTRY_COUNT:
            break
        try:
            sector = build_industry_sector(ak, boards, board_row, len(sectors))
            if sector["trading"]:
                sectors.append(sector)
        except Exception as exc:
            name = get_value(board_row, ["板块名称", "行业名称"], "未知行业")
            errors.append(f"{name}: {exc}")

    if not sectors:
        raise RuntimeError("没有生成任何行业板块数据；" + "；".join(errors))

    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "source": "AkShare/东方财富行业板块",
        "errors": errors,
        "sectors": sectors,
    }


def generate_ths_industries(ak):
    boards = ak.stock_board_industry_summary_ths()
    if "板块" not in boards.columns:
        raise RuntimeError(f"同花顺行业汇总接口缺少板块字段：{list(boards.columns)}")

    sectors = []
    errors = []
    code_map = ths_industry_codes(ak)
    headers = ths_headers()
    board_rows = sorted(boards.to_dict("records"), key=board_heat, reverse=True)
    for board_row in board_rows:
        if len(sectors) >= TOP_INDUSTRY_COUNT:
            break
        try:
            sector = build_ths_sector(ak, code_map, headers, board_row, len(sectors))
            if sector["trading"]:
                sectors.append(sector)
        except Exception as exc:
            name = get_value(board_row, ["板块", "板块名称", "行业名称"], "未知行业")
            errors.append(f"{name}: {exc}")

    if not sectors:
        raise RuntimeError("没有生成任何同花顺行业数据；" + "；".join(errors))

    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "source": "AkShare/同花顺行业板块",
        "errors": errors,
        "sectors": sectors,
    }


def generate():
    try:
        return generate_akshare()
    except Exception as exc:
        payload = generate_sina()
        payload["errors"] = [f"AkShare/东方财富不可用，已切换新浪行情：{exc}"]
        return payload


def write_js(payload):
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = "window.SECTOR_DATA = "
    text += json.dumps(payload, ensure_ascii=False, indent=2)
    text += ";\n"
    OUT_FILE.write_text(text, encoding="utf-8")


def main():
    payload = generate()
    write_js(payload)
    print(f"generated {OUT_FILE}")
    print(f"sectors: {len(payload['sectors'])}")
    if payload.get("errors"):
        print("warnings:")
        for item in payload["errors"]:
            print(f"- {item}")


if __name__ == "__main__":
    main()
