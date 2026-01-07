import requests
import json
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import time

# 币安主流币名单
SYMBOLS = ['BTCUSDT','ETHUSDT','BNBUSDT','XRPUSDT','SOLUSDT','TRXUSDT','DOGEUSDT','ADAUSDT','BCHUSDT','LINKUSDT','XMRUSDT','ZECUSDT','XLMUSDT','LTCUSDT','SUIUSDT','AVAXUSDT','HBARUSDT','SHIBUSDT','CROUSDT','TONUSDT','UNIUSDT','DOTUSDT','AAVEUSDT','TAOUSDT','FTMUSDT','NEARUSDT','ETCUSDT','ICPUSDT','PEPEUSDT','ENAUSDT','MKRUSDT','WLDUSDT','ONDOUSDT','APTUSDT','POLUSDT','ARBUSDT','ALGOUSDT','ATOMUSDT','FILUSDT','VETUSDT','SEIUSDT','BONKUSDT','RENDERUSDT','CAKEUSDT','JUPUSDT','OPUSDT','FETUSDT','LDOUSDT','STXUSDT','TIAUSDT','GALAUSDT','PENDLEUSDT','THETAUSDT','NEOUSDT','RUNEUSDT','INJUSDT','DYDXUSDT','STRKUSDT','GRTUSDT','FLOKIUSDT','JASMYUSDT','ZKUSDT','SANDUSDT','EIGENUSDT','HNTUSDT','FLOWUSDT','EOSUSDT','COMPUSDT','RAYUSDT','MANAUSDT','ARUSDT','LUNCUSDT','1INCHUSDT','XECUSDT','GLMUSDT','EGLDUSDT','FTTUSDT','SFPUSDT','RSRUSDT','NEIROUSDT','APEUSDT','JTOUSDT','ATHUSDT','SNXUSDT','AXSUSDT','LPTUSDT']

# 备用 API 线路
API_NODES = ["https://api1.binance.com", "https://api2.binance.com", "https://api3.binance.com"]

def get_indicators(symbol, node):
    try:
        url = f"{node}/api/v3/klines?symbol={symbol}&interval=1d&limit=200"
        resp = requests.get(url, timeout=10).json()
        if not isinstance(resp, list): return None
        
        df = pd.DataFrame(resp).iloc[:, [4, 7, 10]].astype(float)
        df.columns = ['close', 'vol_quote', 'taker_quote']
        
        current_price = df['close'].iloc[-1]
        ema21 = ta.ema(df['close'], length=21).iloc[-1]
        rsi = ta.rsi(df['close'], length=14).iloc[-1]
        
        current_vol = df['vol_quote'].iloc[-1]
        avg_vol = df['vol_quote'].tail(6).iloc[:-1].mean() 
        
        # 计算创高天数
        closes = df['close'].tolist()
        high_days = 0
        for i in range(len(closes)-2, -1, -1):
            if closes[-1] > closes[i]: high_days += 1
            else: break
            
        return {
            "bias": round(((current_price - ema21) / ema21) * 100, 2),
            "rvol": round(current_vol / avg_vol, 2) if avg_vol > 0 else 1.0,
            "tbr": round((df['taker_quote'].iloc[-1] / current_vol) * 100, 1),
            "rsi": round(rsi, 1),
            "highDays": high_days
        }
    except:
        return None

def main():
    print("正在寻找可用线路...")
    tickers = None
    active_node = ""
    
    for node in API_NODES:
        try:
            print(f"尝试连接: {node}")
            resp = requests.get(f"{node}/api/v3/ticker/24hr", timeout=10).json()
            if isinstance(resp, list):
                tickers = resp
                active_node = node
                print(f"✅ 成功连接: {node}")
                break
            else:
                print(f"❌ 线路 {node} 返回错误: {resp.get('msg')}")
        except:
            continue

    if not tickers:
        print("🚨 所有线路均不可用，请稍后再试或检查币安状态")
        return

    usdt_pairs = [t for t in tickers if t['symbol'] in SYMBOLS]
    top_gainers = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']), reverse=True)[:30]
    top_losers = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']))[:30]
    
    must_analyze = list(set([t['symbol'] for t in top_gainers] + [t['symbol'] for t in top_losers]))
    
    indicator_map = {}
    for s in must_analyze:
        print(f"深度分析: {s}")
        res = get_indicators(s, active_node)
        if res: indicator_map[s] = res
        time.sleep(0.1)

    bj_time = datetime.utcnow() + timedelta(hours=8)
    
    def build_entry(t):
        ind = indicator_map.get(t['symbol'], {"bias":0.0, "rvol":1.0, "tbr":50.0, "rsi":50.0, "highDays":0})
        return {
            "s": t['symbol'], "c": t['priceChangePercent'], "v": t['quoteVolume'], "p": t['lastPrice'],
            **ind
        }

    final_result = {
        "date": bj_time.strftime("%Y-%m-%d"),
        "update_time": bj_time.strftime("%H:%M:%S"),
        "gainers": [build_entry(t) for t in top_gainers],
        "losers": [build_entry(t) for t in top_losers]
    }
    
    with open('last_scan.json', 'w') as f:
        json.dump(final_result, f)
    print("今日数据已存盘至 last_scan.json")

if __name__ == "__main__":
    main()
