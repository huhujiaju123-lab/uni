#!/usr/bin/env python3
"""
纳斯达克股票 PE 分位值分析 Web 应用
支持实时查询、筛选和排序
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__, static_folder='static')
CORS(app)

# 股票列表缓存
STOCK_LISTS = {
    'nasdaq100': [
        "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "AVGO", "COST", "PEP",
        "CSCO", "ADBE", "NFLX", "AMD", "CMCSA", "TMUS", "INTC", "INTU", "TXN", "QCOM",
        "AMGN", "HON", "AMAT", "ISRG", "BKNG", "SBUX", "VRTX", "MDLZ", "GILD", "ADI",
        "ADP", "LRCX", "REGN", "PANW", "MU", "KLAC", "SNPS", "CDNS", "PYPL", "MELI",
        "CSX", "ASML", "CRWD", "MAR", "ORLY", "MNST", "CTAS", "NXPI", "MRVL", "ADSK",
        "CHTR", "PCAR", "WDAY", "DXCM", "FTNT", "AEP", "KDP", "ROST", "CPRT", "PAYX",
        "AZN", "ODFL", "KHC", "LULU", "MCHP", "EXC", "IDXX", "EA", "CTSH", "VRSK",
        "GEHC", "FAST", "BKR", "FANG", "XEL", "BIIB", "DLTR", "CEG", "ON", "TTD",
        "ARM", "DASH", "COIN", "ABNB", "ZM", "PLTR"
    ],
    'china_adr': [
        ("PDD", "拼多多"), ("BIDU", "百度"), ("JD", "京东"), ("NTES", "网易"),
        ("BABA", "阿里巴巴"), ("BILI", "哔哩哔哩"), ("IQ", "爱奇艺"), ("TME", "腾讯音乐"),
        ("WB", "微博"), ("ATHM", "汽车之家"), ("MOMO", "挚文集团"), ("VIPS", "唯品会"),
        ("DDL", "叮咚买菜"), ("MNSO", "名创优品"), ("TAL", "好未来"), ("EDU", "新东方"),
        ("DAO", "有道"), ("NIO", "蔚来"), ("XPEV", "小鹏汽车"), ("LI", "理想汽车"),
        ("FUTU", "富途控股"), ("TIGR", "老虎证券"), ("LX", "乐信"), ("QFIN", "360数科"),
        ("FINV", "信也科技"), ("LKNCY", "瑞幸咖啡"), ("ZH", "知乎"), ("GDS", "万国数据"),
        ("TCOM", "携程"), ("SOHU", "搜狐"), ("YUMC", "百胜中国"), ("YMM", "满帮集团")
    ]
}

# 中概股名称映射
CHINA_ADR_NAMES = {ticker: name for ticker, name in STOCK_LISTS['china_adr']}


def calculate_pe_percentile(ticker, years=3):
    """计算单只股票的 PE 分位值"""
    try:
        stock = yf.Ticker(ticker)

        # 获取历史数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years*365)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty or len(hist) < 50:
            return None

        # 获取公司信息
        info = stock.info
        company_name = info.get('shortName', info.get('longName', ticker))
        current_price = info.get('currentPrice', info.get('regularMarketPrice', None))
        trailing_pe = info.get('trailingPE', None)
        forward_pe = info.get('forwardPE', None)
        market_cap = info.get('marketCap', None)
        sector = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')

        # 其他指标
        pb_ratio = info.get('priceToBook', None)
        ps_ratio = info.get('priceToSalesTrailing12Months', None)
        dividend_yield = info.get('dividendYield', None)
        fifty_two_week_high = info.get('fiftyTwoWeekHigh', None)
        fifty_two_week_low = info.get('fiftyTwoWeekLow', None)

        current_pe = trailing_pe if trailing_pe else forward_pe

        if current_pe is None or current_pe <= 0 or current_pe > 1000:
            return None

        trailing_eps = info.get('trailingEps', None)

        if trailing_eps is None or trailing_eps <= 0:
            return None

        # 计算历史 PE
        hist['PE'] = hist['Close'] / trailing_eps
        hist = hist[(hist['PE'] > 0) & (hist['PE'] < 1000)]

        if len(hist) < 50:
            return None

        # 计算百分位
        pe_series = hist['PE'].values
        percentile = (pe_series < current_pe).sum() / len(pe_series) * 100

        # 计算价格百分位
        price_series = hist['Close'].values
        price_percentile = (price_series < current_price).sum() / len(price_series) * 100 if current_price else None

        # 统计数据
        pe_min = float(pe_series.min())
        pe_max = float(pe_series.max())
        pe_median = float(np.median(pe_series))
        pe_mean = float(pe_series.mean())

        # 格式化市值
        if market_cap:
            if market_cap >= 1e12:
                market_cap_str = f"{market_cap/1e12:.2f}T"
                market_cap_num = market_cap / 1e9
            elif market_cap >= 1e9:
                market_cap_str = f"{market_cap/1e9:.2f}B"
                market_cap_num = market_cap / 1e9
            else:
                market_cap_str = f"{market_cap/1e6:.2f}M"
                market_cap_num = market_cap / 1e6
        else:
            market_cap_str = "N/A"
            market_cap_num = 0

        # 中文名称
        cn_name = CHINA_ADR_NAMES.get(ticker, '')

        return {
            'ticker': ticker,
            'company_name': company_name,
            'company_name_cn': cn_name,
            'sector': sector,
            'industry': industry,
            'current_price': round(current_price, 2) if current_price else None,
            'current_pe': round(current_pe, 2),
            'pe_percentile': round(percentile, 1),
            'price_percentile': round(price_percentile, 1) if price_percentile else None,
            'pe_min_3y': round(pe_min, 2),
            'pe_max_3y': round(pe_max, 2),
            'pe_median_3y': round(pe_median, 2),
            'pe_mean_3y': round(pe_mean, 2),
            'pb_ratio': round(pb_ratio, 2) if pb_ratio else None,
            'ps_ratio': round(ps_ratio, 2) if ps_ratio else None,
            'dividend_yield': round(dividend_yield * 100, 2) if dividend_yield else None,
            'fifty_two_week_high': round(fifty_two_week_high, 2) if fifty_two_week_high else None,
            'fifty_two_week_low': round(fifty_two_week_low, 2) if fifty_two_week_low else None,
            'market_cap': market_cap_str,
            'market_cap_num': market_cap_num,
            'data_points': len(pe_series),
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    except Exception as e:
        print(f"Error processing {ticker}: {e}")
        return None


@app.route('/')
def index():
    """主页"""
    return send_from_directory('static', 'index.html')


@app.route('/api/stock/<ticker>')
def get_stock(ticker):
    """获取单只股票数据"""
    ticker = ticker.upper()
    result = calculate_pe_percentile(ticker)

    if result:
        return jsonify({'success': True, 'data': result})
    else:
        return jsonify({'success': False, 'error': f'无法获取 {ticker} 的数据'})


@app.route('/api/batch', methods=['POST'])
def get_batch():
    """批量获取股票数据"""
    data = request.get_json()
    tickers = data.get('tickers', [])

    results = []
    for ticker in tickers:
        result = calculate_pe_percentile(ticker.upper())
        if result:
            results.append(result)

    return jsonify({'success': True, 'data': results, 'total': len(results)})


@app.route('/api/list/<list_name>')
def get_list(list_name):
    """获取预设股票列表"""
    if list_name == 'nasdaq100':
        tickers = STOCK_LISTS['nasdaq100']
    elif list_name == 'china_adr':
        tickers = [t[0] for t in STOCK_LISTS['china_adr']]
    else:
        return jsonify({'success': False, 'error': '未知的列表名称'})

    results = []
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{total}] Processing {ticker}...")
        result = calculate_pe_percentile(ticker)
        if result:
            results.append(result)

    # 按 PE 百分位排序
    results.sort(key=lambda x: x['pe_percentile'])

    return jsonify({
        'success': True,
        'data': results,
        'total': len(results),
        'list_name': list_name
    })


@app.route('/api/search')
def search():
    """搜索股票"""
    query = request.args.get('q', '').upper()

    if not query or len(query) < 1:
        return jsonify({'success': False, 'error': '请输入搜索关键词'})

    # 直接尝试作为股票代码查询
    result = calculate_pe_percentile(query)

    if result:
        return jsonify({'success': True, 'data': [result]})
    else:
        return jsonify({'success': False, 'error': f'未找到股票 {query}'})


@app.route('/api/filter', methods=['POST'])
def filter_stocks():
    """筛选股票"""
    data = request.get_json()
    stocks = data.get('stocks', [])

    # 筛选条件
    pe_min = data.get('pe_min')
    pe_max = data.get('pe_max')
    percentile_min = data.get('percentile_min')
    percentile_max = data.get('percentile_max')
    sector = data.get('sector')
    sort_by = data.get('sort_by', 'pe_percentile')
    sort_order = data.get('sort_order', 'asc')

    filtered = stocks

    if pe_min is not None:
        filtered = [s for s in filtered if s['current_pe'] >= pe_min]
    if pe_max is not None:
        filtered = [s for s in filtered if s['current_pe'] <= pe_max]
    if percentile_min is not None:
        filtered = [s for s in filtered if s['pe_percentile'] >= percentile_min]
    if percentile_max is not None:
        filtered = [s for s in filtered if s['pe_percentile'] <= percentile_max]
    if sector:
        filtered = [s for s in filtered if s['sector'] == sector]

    # 排序
    reverse = sort_order == 'desc'
    filtered.sort(key=lambda x: x.get(sort_by, 0) or 0, reverse=reverse)

    return jsonify({'success': True, 'data': filtered, 'total': len(filtered)})


if __name__ == '__main__':
    print("=" * 60)
    print("纳斯达克股票 PE 分位值分析系统")
    print("=" * 60)
    print()
    print("访问地址: http://localhost:5001")
    print()
    app.run(host='0.0.0.0', port=5001, debug=True)
