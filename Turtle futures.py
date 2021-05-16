import time
import ccxt
import numpy as np
from numpy.lib.function_base import blackman
import pandas as pd
import datetime
import talib
import pprint

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

def get_condition_max_price(ticker, days, condition):
    """전 봉의 종가 조회"""
    df = get_ohlcv(ticker, days+1)
    price = df[condition].shift(1).max()
    print(price)
    return price

def get_condition_min_price(ticker, days, condition):
    """전 봉의 종가 조회"""
    df = get_ohlcv(ticker, days)
    price = df[condition].shift(1).min()
    print(price)
    return price


def get_current_price(ticker):
    """현재가 조회"""
    orderbook = exchange.fetch_order_book(ticker)
    price = orderbook['asks'][0][0]
    return price

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

def get_ATR(ticker, days):
    df = get_ohlcv(ticker, days*5)
    close = np.array(df['close'])
    high = np.array(df['high'])
    low = np.array(df['low'])
    ATR = talib. ATR(high, low, close, timeperiod=days)[-1]
    return round(ATR, 4)

def buy(ticker):
    """매수조건 확인 후 매수"""
    amount = round((usdt / get_current_price(ticker))* 3, 3)
    time.sleep(1)

    if get_current_price(ticker) > high55:
        exchange.create_market_buy_order(ticker, amount)
        re_condition = "SELL"
        bought_list.append(ticker)
        time.sleep(2)
        stop(re_condition, ticker)
        print('BUY: ' + ticker)
    elif get_current_price(ticker) < low55:
        exchange.create_market_sell_order(ticker, amount)
        re_condition ="BUY"
        bought_list.append(ticker)
        time.sleep(2)
        stop(re_condition, ticker)
        print('SELL: ' + ticker)

def stop(condition, ticker):
    balance = exchange.fetch_balance()['info']['positions']
    time.sleep(2)
    for elem in balance:
        if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
            ticker = str(elem['symbol']).replace('USDT', '/USDT')
            amount = str(elem['positionAmt']).replace('-', '')
            if condition == 'SELL':
                price = get_current_price(ticker) - 2 * get_ATR(ticker, 14)
            elif condition == 'BUY':
                price = get_current_price(ticker) + 2 * get_ATR(ticker, 14)
            exchange.create_order(ticker, 'STOP', condition, amount, price, {'stopPrice': price})

def sell(ticker):
    """매수조건 확인 후 매도"""
    amount = round((usdt / get_current_price(ticker))* 3, 3)
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        if ticker.replace('/USDT', 'USDT') in elem['symbol']:
            if float(elem['positionAmt']) < 0:
                side = 'SELL'
            elif float(elem['positionAmt']) > 0:
                side = 'BUY'
            else:
                side = 'n'
    time.sleep(1)
    
    if get_current_price(ticker) > low20 and side == 'BUY':
        for elem in balance:
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                ticker = str(elem['symbol']).replace('USDT', '/USDT')
                amount = str(elem['positionAmt']).replace('-', '')
                exchange.create_market_sell_order(ticker, amount, {'closePosition':'true'})
            print('Close: ' + ticker)
            sell_list.append(ticker)
    if get_current_price(ticker) < high20 and side == 'SELL':
        for elem in balance:
            if elem['initialMargin'] != '0' and elem['symbol'] == ticker.replace('/USDT', 'USDT'):
                ticker = str(elem['symbol']).replace('USDT', '/USDT')
                amount = str(elem['positionAmt']).replace('-', '')
                exchange.create_market_buy_order(ticker, amount, {'closePosition':'true'})
            print('Close: ' + ticker)
            sell_list.append(ticker)

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

exchange = ccxt.binance(config={
    'apiKey': api_key,
    'secret': secret,
    'enableRateLimit': True, # required https://github.com/ccxt/ccxt/wiki/Manual#rate-limit
    'options': {
        'defaultType': 'future',
    }
})

buy_list = ['ETH/USDT', 'XRP/USDT', 'ADA/USDT']
bought_list = []
sell_list = []
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
                high55 = get_condition_max_price(ticker,55,'high')
                high20 = get_condition_max_price(ticker,20,'high')
                low55 = get_condition_min_price(ticker,55,'low')
                low20 = get_condition_min_price(ticker,20,'low')
                if ticker not in bought_list:
                    buy(ticker)
                if ticker in bought_list and ticker not in sell_list:
                    sell(ticker)
        update_boughtlist()
        time.sleep(1)
    except Exception as e:
        print(e)
        pass