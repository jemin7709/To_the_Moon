import time
import ccxt
import numpy as np
import pandas as pd
import datetime
import talib

with open("바이낸스.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip() 
    secret = lines[1].strip() 

def get_ohlcv(ticker, days):
    """ohlcv 조회"""
    ohlcv = exchange.fetch_ohlcv(ticker, timeframe='15m', limit=days)
    df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
    df.set_index('datetime', inplace=True)
    return df

def get_noise(df):
    """k값으로 사용할 노이즈 계산"""
    o =  np.array(df['open'])
    h = np.array(df['high'])
    l = np.array(df['low'])
    c = np.array(df['close'])
    noise = np.mean(1 - abs(o - c) / (h - l))
    return noise

def get_ATR(ticker, days):
    df = get_ohlcv(ticker, days ** 2)
    close = np.array(df['close'])
    high = np.array(df['high'])
    low = np.array(df['low'])
    ATR = talib. ATR(high, low, close, timeperiod=days)[-1]
    return round(ATR, 4)

def get_target_long_price(noise, df):
    o =  np.array(df['open'])
    h = np.array(df['high'])
    l = np.array(df['low'])
    """변동성 돌파 전략으로 매수 목표가 조회"""
    target_price = o[1] + (h[0] - l[0]) * noise
    return target_price

def get_target_short_price(noise, df):
    o =  np.array(df['open'])
    h = np.array(df['high'])
    l = np.array(df['low'])
    """변동성 돌파 전략으로 매수 목표가 조회"""
    target_price = o[1] - (h[0] - l[0]) * noise
    return target_price

def get_ex_volatility(df):
    h = np.array(df['high'])
    l = np.array(df['low'])
    c = np.array(df['close'])
    vol = ((h[0] - l[0]) / c[0]) * 100
    return vol

def get_current_price(ticker):
    """현재가 조회"""
    orderbook = exchange.fetch_order_book(ticker)
    price = orderbook['asks'][0][0]
    return price

def get_ma(df):
    """이동 평균선 조회"""
    c = np.array(df['close'])
    ma3 = np.mean(c[-3:])
    ma5 = np.mean(c[-5:])
    ma10 = np.mean(c[-10:])
    ma20 = np.mean(c[-20:])
    return ma3, ma5, ma10, ma20

def get_ma_score(curentP, df, condition):
    ma3, ma5, ma10, ma20 = get_ma(df)
    score = 0
    if condition == 'LONG':
        if curentP > ma3:
            score += 0.25
        if curentP > ma5:
            score += 0.25
        if curentP > ma10:
            score += 0.25
        if curentP > ma20:
            score += 0.25
    else:
        if curentP < ma3:
            score += 0.25
        if curentP < ma5:
            score += 0.25
        if curentP < ma10:
            score += 0.25
        if curentP < ma20:
            score += 0.25
    return score

def buy(ticker):
    df20 = get_ohlcv(ticker, 20)
    df2 = get_ohlcv(ticker, 2)
    noise = get_noise(df20)
    targetLP = get_target_long_price(noise, df2)
    targetSP = get_target_short_price(noise, df2)
    curentP = get_current_price(ticker)
    vol = get_ex_volatility(df2)
    print('Long: ' + str(targetLP))
    print('Sohrt: ' + str(targetSP))
    if vol > 1:
        _usdt = usdt * (1 / vol)
    else:
        _usdt = usdt
    if curentP > targetLP:
        _usdt = _usdt * get_ma_score(curentP, df20, "LONG")
        amount = round(_usdt / (curentP), 3) 
        exchange.create_market_buy_order(ticker, amount)
        print('BUY: ' + ticker)
        bought_list.append(ticker)
    elif curentP < targetSP:
        _usdt = _usdt * get_ma_score(curentP, df20, "SHORT")
        amount = round(_usdt / (curentP), 3) 
        exchange.create_market_sell_order(ticker, amount)
        print('SELL: ' + ticker)
        bought_list.append(ticker)

def buy2(ticker):
    df2 = get_ohlcv(ticker, 2)
    market = get_ATR(df2)
    IBS = get_IBS(df2)
    curentP = get_current_price(ticker)
    amount = round(usdt / (curentP), 3) 
    if market and IBS < 0.2:
        exchange.create_market_buy_order(ticker, amount)
        print('BUY: ' + ticker)
        bought_list.append(ticker)
    elif not market and IBS > 0.8:
        exchange.create_market_sell_order(ticker, amount)
        print('SELL: ' + ticker)
        bought_list.append(ticker)

def stop(ticker):
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        amount = float(elem['positionAmt'])
        sl = float(elem['initialMargin']) * -0.003
        pnl = float(elem['unrealizedProfit'])
        if 'USDT' in ticker and pnl < 0 and pnl < sl:
            print(sl)
            print(pnl)
            if amount > 0:
                if elem['initialMargin'] != '0':
                    amount = str(amount).replace('-', '')
                    exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                    print('Close: ' + ticker)
                    bought_list.remove(ticker)
            elif  amount < 0:        
                if elem['initialMargin'] != '0':
                    amount = str(amount).replace('-', '')
                    exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                    print('Close: ' + ticker)
                    bought_list.remove(ticker)

def sell():
    balance = exchange.fetch_balance()['info']['positions']
    for elem in balance:
        ticker = str(elem['symbol']).replace('USDT', '/USDT')
        amount = float(elem['positionAmt'])
        if 'USDT' in ticker:
            if amount > 0:
                if elem['initialMargin'] != '0':
                    amount = str(amount).replace('-', '')
                    exchange.create_market_sell_order(ticker, amount, {'reduceOnly':'true'})
                    print('Close: ' + ticker)
                    bought_list.remove(ticker)
            elif  amount < 0:        
                if elem['initialMargin'] != '0':
                    amount = str(amount).replace('-', '')
                    exchange.create_market_buy_order(ticker, amount, {'reduceOnly':'true'})
                    print('Close: ' + ticker)
                    bought_list.remove(ticker)

def get_IBS(df):
    h = np.array(df['high'])
    l = np.array(df['low'])
    c = np.array(df['close'])
    IBS = ((c[0] - l[0]) / (h[0] - l[0]))
    return IBS

def get_market(df):
    o = np.array(df['open'])
    c = np.array(df['close'])
    if o[1] < c[1]:
        return True
    elif o[1] > c[1]:
        return False

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

buy_list = ['ETH/USDT', 'BTC/USDT']
bought_list = []
usdt = exchange.fetch_balance()['USDT']['free'] / len(buy_list)
balance = exchange.fetch_balance()['info']['positions']
# for elem in balance:
#     if elem['initialMargin'] != '0' and ('USDT' in str(elem['symbol'])):
#         ticker = str(elem['symbol']).replace('USDT', '/USDT')
#         bought_list.append(ticker)

print('start')
while True:
    try:
        hour = datetime.datetime.now().hour
        minute = datetime.datetime.now().minute % 15
        second = datetime.datetime.now().second
        print(str(minute) + ' and ' + str(second))
        if len(bought_list) == 0:
            usdt = exchange.fetch_balance()['USDT']['free'] / len(buy_list)
        if  minute == 0 and 1 <= second <= 5:
            sell()
        else:
            for ticker in buy_list:
                if ticker not in bought_list:
                    buy(ticker)
                if ticker in bought_list:
                    stop(ticker)
        time.sleep(0.1)
    except Exception as e:
        print(e)

#시간측정용 코드 
#start = time.time()
#print("time :", time.time() - start)