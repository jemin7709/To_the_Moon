import time
import ccxt
import numpy as np
import pandas as pd
import talib

with open("바이낸스.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip() 
    secret = lines[1].strip() 

def get_ohlcv(ticker, days):
    """ohlcv 조회"""
    ohlcv = exchange.fetch_ohlcv(ticker, timeframe='1m', limit=days)
    df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df

def get_ATR(ticker, days):
    df = get_ohlcv(ticker, days * days)
    close = np.array(df['close'])
    high = np.array(df['high'])
    low = np.array(df['low'])
    ATR = talib. ATR(high, low, close, timeperiod=days)[-1]
    return round(ATR, 4)

def get_condition_max_price(ticker, days, condition, delay = 0):
    """전 봉의 종가 조회"""
    df = get_ohlcv(ticker, days+delay)
    price = df[condition][:days-delay].max()
    return price

def get_condition_min_price(ticker, days, condition, delay = 0):
    """전 봉의 종가 조회"""
    df = get_ohlcv(ticker, days+delay)
    price = df[condition][:days-delay].min()
    return price

def get_current_price(ticker):
    """현재가 조회"""
    orderbook = exchange.fetch_order_book(ticker)
    price = orderbook['asks'][0][0]
    return price

def sell_all():
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        amount = str(elem['positionAmt']).replace('-', '')
        if float(elem['positionAmt']) > 0:
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)
        elif  float(elem['positionAmt']) < 0:        
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)

def buy(ticker):
    """매수조건 확인 후 매수"""
    usdt_1p = usdt * 0.01 / (2 * get_ATR(ticker, 14))
    amount = round(usdt_1p, 4)
    print(amount)
    if exhigh60 < get_condition_max_price(ticker,1,'high'):
        exchange.create_market_buy_order(ticker, amount)
        re_condition = "SELL"
        bought_list.append(ticker)
        time.sleep(1.5)
        stop(re_condition, ticker)
        print('BUY: ' + ticker)
    elif exlow60 > get_condition_min_price(ticker,1,'low'):
        exchange.create_market_sell_order(ticker, amount)
        re_condition ="BUY"
        bought_list.append(ticker)
        time.sleep(1.5)
        stop(re_condition, ticker)
        print('SELL: ' + ticker)

def stop(condition, ticker):
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
            ticker = str(elem['symbol']).replace('USDT', '/USDT')
            amount = str(elem['positionAmt']).replace('-', '')
            atr = get_ATR(ticker, 14)
            if condition == 'SELL':
                price = get_current_price(ticker) - 2 * atr
                profit_price = get_current_price(ticker) + 3 * atr
            elif condition == 'BUY':
                price = get_current_price(ticker) + 2 * atr
                profit_price = get_current_price(ticker) - 3 * atr
            exchange.create_order(ticker, 'STOP', condition, amount, price, {'stopPrice': price})
            #exchange.createOrder(ticker, 'TAKE_PROFIT', condition, amount, profit_price, {'stopPrice': profit_price})
def sell(ticker):
    """매수조건 확인 후 매도"""
    balance = exchange.fetch_balance()['info']['positions']
    side = ""
    for elem in balance:
        if ticker.replace('/USDT', 'USDT') == elem['symbol']:
            if  float(elem['positionAmt']) < 0:
                side = 'SELL'
            elif float(elem['positionAmt']) > 0:
                side = 'BUY'
    if exlow10 > get_condition_min_price(ticker,1,'low') and side == 'BUY':
        for elem in balance:
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                ticker = str(elem['symbol']).replace('USDT', '/USDT')
                amount = str(elem['positionAmt']).replace('-', '')
                exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)
    if exhigh10 < get_condition_max_price(ticker,1,'high') and side == 'SELL':
        for elem in balance:
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                ticker = str(elem['symbol']).replace('USDT', '/USDT')
                amount = str(elem['positionAmt']).replace('-', '')
                exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                print('Close: ' + ticker)

def update_boughtlist():
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        if elem['initialMargin'] == '0' and ticker in bought_list:
            order = exchange.fetchOpenOrders(ticker)
            bought_list.remove(ticker)
            for elem in order:
                exchange.cancel_order(elem['id'], ticker)

exchange = ccxt.binance(config={
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True, # required https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
        'enableRateLimit': True
    }
})

buy_list = ['ETH/USDT']
bought_list = []
balance = exchange.fetch_balance()['info']['positions']
for elem in balance:
    if elem['initialMargin'] != '0' and ('ETH' in str(elem['symbol'])):
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        bought_list.append(ticker)
usdt = exchange.fetch_balance()['USDT']['free'] / 10
print('start')
while True:
    try:
        if len(bought_list)==0:
            usdt = exchange.fetch_balance()['USDT']['free'] / 10
        for ticker in buy_list:
            exhigh60 = get_condition_max_price(ticker, 20,'high', 1)
            exhigh10 = get_condition_max_price(ticker, 5,'high', 1)
            exlow60 = get_condition_min_price(ticker, 20, 'low', 1)
            exlow10 = get_condition_min_price(ticker, 5, 'low', 1)
            if ticker not in bought_list:
                print(ticker + 'buy')
                buy(ticker)
            if ticker in bought_list:
                print(ticker + 'sell')
                sell(ticker)
        update_boughtlist()
    except Exception as e:
        print(e)
        pass
