import requests
import json
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import time

# 币安 207 个主流币名单
SYMBOLS = ['BTCUSDT','ETHUSDT','BNBUSDT','XRPUSDT','SOLUSDT','TRXUSDT','DOGEUSDT','ADAUSDT','BCHUSDT','LINKUSDT','XMRUSDT','ZECUSDT','XLMUSDT','LTCUSDT','SUIUSDT','AVAXUSDT','HBARUSDT','SHIBUSDT','CROUSDT','TONUSDT','UNIUSDT','DOTUSDT','AAVEUSDT','TAOUSDT','FTMUSDT','NEARUSDT','ETCUSDT','ICPUSDT','PEPEUSDT','ENAUSDT','MKRUSDT','WLDUSDT','ONDOUSDT','APTUSDT','POLUSDT','ARBUSDT','ALGOUSDT','ATOMUSDT','FILUSDT','VETUSDT','SEIUSDT','BONKUSDT','RENDERUSDT','CAKEUSDT','JUPUSDT','OPUSDT','FETUSDT','LDOUSDT','STXUSDT','TIAUSDT','GALAUSDT','PENDLEUSDT','THETAUSDT','NEOUSDT','RUNEUSDT','INJUSDT','DYDXUSDT','STRKUSDT','GRTUSDT','FLOKIUSDT','JASMYUSDT','ZKUSDT','SANDUSDT','EIGENUSDT','HNTUSDT','FLOWUSDT','EOSUSDT','COMPUSDT','RAYUSDT','MANAUSDT','ARUSDT','LUNCUSDT','1INCHUSDT','XECUSDT','GLMUSDT','EGLDUSDT','FTTUSDT','SFPUSDT','RSRUSDT','NEIROUSDT','APEUSDT','JTOUSDT','ATHUSDT','SNXUSDT','AXSUSDT','LPTUSDT']

BASE_URL = "https://api1.binance.com"

def calculate_high_days(closes):
    current = closes[-1]
    count = 0
    for i in range(len(closes)-2, -1, -1):
        if current > closes[i]: count += 1
        else: break
    return count

def get_indicators(symbol):
    try:
        # 获取日线 K 线用于计算热力榜指标
        resp = requests.get(f"{BASE_URL}/api/v3/klines?symbol={symbol}&interval=1d&limit=200", timeout=10).json()
        df = pd.DataFrame(resp).iloc[:, [4, 7, 10]].astype(float)
        df.columns = ['close', 'vol_quote', 'taker_quote']
        
        current_price = df['close'].iloc[-1]
        ema21 = ta.ema(df['close'], length=21).iloc[-1]
        rsi = ta.rsi(df['close'], length=14).iloc[-1]
        
        current_vol = df['vol_quote'].iloc[-1]
        avg_vol = df['vol_quote'].tail(6).iloc[:-1].mean() 
        
        return {
            "bias": round(((current_price - ema21) / ema21) * 100, 2),
            "rvol": round(current_vol / avg_vol, 2) if avg_vol > 0 else 1.0,
            "tbr": round((df['taker_quote'].iloc[-1] / current_vol) * 100, 1),
            "rsi": round(rsi, 1),
            "highDays": calculate_high_days(df['close'].tolist())
        }
    except:
        return {"bias": 0.0, "rvol": 1.0, "tbr": 50.0, "rsi": 50.0, "highDays": 0}

def main():
    print("开始获取全市场行情...")
    tickers = requests.get(f"{BASE_URL}/api/v3/ticker/24hr").json()
    usdt_pairs = [t for t in tickers if t['symbol'] in SYMBOLS]
    
    top_gainers = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']), reverse=True)[:30]
    top_losers = sorted(usdt_pairs, key=lambda x: float(x['priceChangePercent']))[:30]
    
    # 确定需要深度计算指标的 60 个币种
    must_analyze = list(set([t['symbol'] for t in top_gainers] + [t['symbol'] for t in top_losers]))
    
    indicator_map = {}
    for s in must_analyze:
        print(f"正在计算指标: {s}")
        indicator_map[s] = get_indicators(s)
        time.sleep(0.1) # 保护频率

    bj_time = datetime.utcnow() + timedelta(hours=8)
    
    def build_data(t):
        ind = indicator_map.get(t['symbol'], {})
        return {
            "s": t['symbol'],
            "c": t['priceChangePercent'],
            "v": t['quoteVolume'],
            "p": t['lastPrice'],
            **ind
        }

    final_result = {
        "date": bj_time.strftime("%Y-%m-%d"),
        "update_time": bj_time.strftime("%H:%M:%S"),
        "gainers": [build_data(t) for t in top_gainers],
        "losers": [build_data(t) for t in top_losers]
    }
    
    with open('last_scan.json', 'w') as f:
        json.dump(final_result, f)
    print("今日数据已存盘至 last_scan.json")

if __name__ == "__main__":
    main()
