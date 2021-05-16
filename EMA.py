import time
import ccxt
import numpy
import pandas as pd
import datetime

with open("바이낸스.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip() 
    secret = lines[1].strip() 

def get_ohlcv(ticker, days):
    """ohlcv 조회"""
    ohlcv = exchange.fetch_ohlcv(ticker, timeframe='5m', limit=days)
    df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df

def get_ma(ticker, days):
    """이동 평균선 조회"""
    df = get_ohlcv(ticker, days)
    ma = df['close'].rolling(days, min_periods=1).mean().iloc[-1]
    return round(ma, 4)

def get_ema(ticker, days, prices='close', smoothing=2):
    df = get_ohlcv(ticker, days)
    ema = [sum(df[prices][:days]) / days]
    for price in prices[days:]:
        ema.append((price * (smoothing / (1 + days))) + ema[-1] * (1 - (smoothing / (1 + days))))
    return round(ema[0], 4)


def get_open_price(ticker):
    """시가 조회"""
    df = get_ohlcv(ticker, 1)
    price = df['open'].iloc[-1]
    return price

def get_condition_price(ticker, days, condition):
    """전 봉의 종가 조회"""
    df = get_ohlcv(ticker, days + 1 )
    price = df[condition].shift(days).iloc[-1]
    return price

def get_current_price(ticker):
    """현재가 조회"""
    orderbook = exchange.fetch_order_book(ticker)
    price = orderbook['asks'][0][0]
    return price

def buy(ticker):
    """매수조건 확인 후 매수"""
    ema25 = get_ema(ticker, 25)
    ema50 = get_ema(ticker, 50)
    ema100 = get_ema(ticker, 100)
    amount = round(usdt / get_current_price(ticker) * 3, 3)
    re_condition = ""
    if ema25 > ema50 > ema100:
        if (ema25 > get_condition_price(ticker, 2, 'close') > ema50 or get_condition_price(ticker, 2, 'close') < ema50) and get_condition_price(ticker, 1, 'close') > ema25:
            exchange.create_market_buy_order(ticker, amount)
            re_condition = "SELL"
            bought_list.append(ticker)
            time.sleep(2)
            sell(re_condition, ticker)
            print('BUY: ' + ticker)
    elif ema25 < ema50 < ema100:
        if (ema25 < get_condition_price(ticker, 2, 'close') < ema50 or get_condition_price(ticker, 2, 'close') > ema50) and get_condition_price(ticker, 1, 'close') < ema25:
            exchange.create_market_sell_order(ticker, amount)
            re_condition ="BUY"
            bought_list.append(ticker)
            time.sleep(2)
            sell(re_condition, ticker)
            print('SELL: ' + ticker)
            

def sell(condition, ticker):
    balance = exchange.fetch_balance()['info']['positions']
    time.sleep(2)
    for elem in balance:
        if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
            ticker = str(elem['symbol']).replace('USDT', '/USDT')
            amount = str(elem['positionAmt']).replace('-', '')
            price = get_ema(ticker, 50)
            profit_price = abs((get_current_price(ticker) - price))
            if condition == "SELL":
                profit_price = get_current_price(ticker) + profit_price * 1.5
            elif condition == "BUY":
                profit_price = get_current_price(ticker) - profit_price * 1.5

            exchange.createOrder(ticker, 'TAKE_PROFIT', condition, amount, profit_price, {'stopPrice': profit_price})
            exchange.create_order(ticker, 'STOP', condition, amount, price, {'stopPrice': price})

def update_boughtlist():
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        if elem['initialMargin'] == '0' and ticker in bought_list:
            order = exchange.fetchOpenOrders(ticker)
            time.sleep(2)
            bought_list.remove(ticker)
            for elem in order:
                    exchange.cancel_order(elem['id'], ticker)


def sell_all():
    balance = exchange.fetch_balance()['info']['positions']
    time.sleep(2)
    for elem in balance:
        if elem['initialMargin'] != '0':
            ticker = str(elem['symbol']).replace('USDT', '/USDT')
            amount = elem['positionAmt']
            exchange.create_market_sell_order(ticker, amount)

exchange = ccxt.binance(config={
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True, # required https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
    'options': {
        'defaultType': 'future',
    }
})

buy_list = ['ETH/USDT', 'XRP/USDT']
bought_list = []
usdt = exchange.fetch_balance()['USDT']['free'] * 0.25
print('start')
while True:
    try:
        now = datetime.datetime.now()
        start_time = now.replace(hour=23, minute=58, second=0)
        end_time = now.replace(hour=23, minute=59, second=0)
        if start_time < now < end_time:
            sell_all()
            usdt = exchange.fetch_balance()['USDT']['free'] * 0.25
        if bought_list != buy_list:
            for ticker in buy_list:
                if ticker not in bought_list:
                    buy(ticker)
        update_boughtlist()
        time.sleep(300)
    except Exception as e:
        print(e)
        pass