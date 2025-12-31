"""
股票判断脚本 V0 - 简洁版（支持数据库）
"""

import sys
sys.path.append('d:/strategy=Z')

from db.api import StockDB
import pandas as pd


def judge(symbol, use_db=False):
    """
    判断股票买卖信号

    Args:
        symbol: 股票代码
        use_db: 是否使用数据库（更快）

    Returns:
        dict: {action, price, score, reasons}
    """
    if use_db:
        # 从数据库读取
        db = StockDB()
        df = db.get_price_history(symbol)

        if df.empty:
            return None

        df = df.rename(columns={'close': 'Close', 'date': 'Date'})
        df['Close'] = df['Close'].astype(float)

        # 计算指标
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()

        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
    else:
        # 直接从 yfinance 获取
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period='6mo')

        if df.empty:
            return None

        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()

        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

    # 最新数据
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    # 判断逻辑
    score = 0
    reasons = []

    # 趋势：多头排列
    if curr['Close'] > curr['MA5'] > curr['MA20'] > curr['MA60']:
        score += 3
        reasons.append("多头排列")
    elif curr['Close'] < curr['MA5'] < curr['MA20'] < curr['MA60']:
        score -= 3
        reasons.append("空头排列")

    # 金叉/死叉
    if prev['MA5'] <= prev['MA20'] and curr['MA5'] > curr['MA20']:
        score += 2
        reasons.append("金叉")
    elif prev['MA5'] >= prev['MA20'] and curr['MA5'] < curr['MA20']:
        score -= 2
        reasons.append("死叉")

    # RSI
    if curr['RSI'] < 30:
        score += 1
        reasons.append("超卖")
    elif curr['RSI'] > 70:
        score -= 1
        reasons.append("超买")

    # 动作
    if score >= 3:
        action = "BUY"
    elif score <= -3:
        action = "SELL"
    else:
        action = "HOLD"

    return {
        'symbol': symbol,
        'action': action,
        'price': curr['Close'],
        'score': score,
        'reasons': reasons
    }


def batch_judge(symbols):
    """批量判断"""
    results = []

    for symbol in symbols:
        result = judge(symbol)
        if result:
            results.append(result)

    # 排序
    results.sort(key=lambda x: x['score'], reverse=True)

    # 输出
    print(f"\n{'Symbol':<8} {'Action':<6} {'Price':<10} {'Score':<6} Reasons")
    print("-" * 60)

    for r in results:
        reasons_str = ', '.join(r['reasons']) if r['reasons'] else '-'
        print(f"{r['symbol']:<8} {r['action']:<6} ${r['price']:<9.2f} {r['score']:<6} {reasons_str}")

    return results


# 使用
if __name__ == "__main__":
    # 单只
    result = judge('AAPL')
    if result:
        print(f"\n{result['symbol']}: {result['action']} @ ${result['price']:.2f}")
        print(f"Score: {result['score']}, Reasons: {result['reasons']}")

    # 批量
    # batch_judge(['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA'])