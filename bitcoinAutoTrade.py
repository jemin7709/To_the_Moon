import time
import pyupbit
import datetime
import traceback

with open("key.txt") as key:
    lines = key.readlines()
    access = lines[0].strip()
    secret = lines[1].strip()

def get_target_price(ticker):
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[1]['open'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * get_noise(ticker, 20)
    return target_price

def get_ma(ticker, days):
    """15일 이동 평균선 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=days)
    ma = df['close'].rolling(days).mean().iloc[-1]
    return ma

def get_noise(ticker, days):
    """k값으로 사용할 노이즈 계산"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=days)
    df['noise'] = 1 - abs(df['open'] - df['close']) / (df['high'] - df['low'])
    noise = df['noise'].rolling(days).mean().iloc[-1]
    return noise


def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return None

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]

def checkBuy(ticker):
    """매수가격확인용"""
    target_price = get_target_price("KRW-" + ticker)
    current_price = get_current_price("KRW-" + ticker)
    target_hold = get_balance(ticker)
    div_krw = int(krw/3)
    krw_score = 0
    noise = get_noise('KRW-' + ticker, 30)
    if  target_hold == None:
        if target_price < current_price:
            if get_ma('KRW-' + ticker, 5) < current_price:
                krw_score += div_krw
            if get_ma('KRW-' + ticker, 10) < current_price:
                krw_score += div_krw
            if get_ma('KRW-' + ticker, 20) < current_price:
                krw_score += div_krw
            if krw_score != 0:
                if krw > 5000:
                    print(ticker + ' BUY')
                    print(noise)
                    upbit.buy_market_order("KRW-"+ticker, krw_score*0.9995)
    return 0

def checkSell(ticker):
    """매도가격확인용"""
    tic = get_balance(ticker)
    if tic != None:
        print(ticker + ' SELL')
        upbit.sell_market_order("KRW-" + ticker, tic)
    return 0

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
krw = int(get_balance("KRW") / 10)
# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC")
        end_time = start_time + datetime.timedelta(days=1) - datetime.timedelta(minutes=5)
        krw_check_time = start_time + datetime.timedelta(days=1) - datetime.timedelta(minutes=1)

        tickers = pyupbit.get_tickers(fiat="KRW")
        mytickers = upbit.get_balances()

        if start_time < now < end_time:
            if len(upbit.get_balances()) < 6:
                for ticker in tickers:
                    ticker = str(ticker).replace("KRW-", "")
                    checkBuy(ticker)
                    time.sleep(1)

        elif end_time < now < krw_check_time:
            for ticker in mytickers:
                if ticker['currency'] != 'KRW':
                    ticker = ticker['currency']
                    checkSell(ticker)
                time.sleep(1)

        else:
            krw = int(get_balance("KRW") / 10)
            print(krw)

        time.sleep(2)
    except Exception as e:
        print(e)
        time.sleep(1)