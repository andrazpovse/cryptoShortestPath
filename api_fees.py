'''

Web scraping exchanges for their withdrawal and exchange fees. Will insert them into DB.

'''


from requests_futures.sessions import FuturesSession
import json
import requests
from bs4 import BeautifulSoup
import re
import time

from pymongo import MongoClient

# for mongodb connection
def connectToDatabase():
    # Naredimo ustrezne strukture v MongoDB
    client = MongoClient('localhost', 27017)
    # ustvari bazo z imenom (ce se ne obstaja)
    db = client['database']



    return db


# list with tuples - (exchange name, API URL)....Only some exchanges have API for withdrawal fees. Others we scrape.
list_of_api_requests = [
    ('kucoin', "https://api.kucoin.com/v1/market/open/coins"),

    ('poloniex', "https://poloniex.com/public?command=returnCurrencies"),

    ('bittrex', "https://bittrex.com/api/v1.1/public/getcurrencies"),

    ('binance', "https://www.binance.com/assetWithdraw/getAllAsset.html")
]



'''
Exchange fees (not in % anymore... 0.1% = 0.001)
'''

KUCOIN_fee_maker = 0.001
KUCOIN_fee_taker = 0.001

POLONIEX_fee_maker = 0.0015
POLONIEX_fee_taker = 0.0025

BITTREX_fee_maker = 0.0025
BITTREX_fee_taker = 0.0025

BINANCE_fee_maker = 0.001
BINANCE_fee_taker = 0.001

BITSTAMP_fee_maker = 0.0025
BITSTAMP_fee_taker = 0.0025

BITFINEX_fee_maker = 0.001
BITFINEX_fee_taker = 0.002

#HITBTC_fee_maker = 0.00
#HITBTC_fee_taker = 0.001

KRAKEN_fee_maker = 0.0016
KRAKEN_fee_taker = 0.0026



def writeToDatabase(db, name, data):
    '''

    :param db: database connection
    :param name: name of the exchange
    :param data: dictonary with all the data on fees
    :return:  1 if everything went ok, 0 else
    '''
    try:
        db.fees.update_one({'name': name}, {'$set': {'time': time.time(), 'data': data}}, upsert=True)
        print('update fees OK database ', name)
    except Exception as exc:
        print('Error when writing to database ', name, ' cause: ', exc)




def updateFees():
    '''
       Ta funkcija se bo klicala vsakih npr. 5 minut. Posodobi podatke v podatkovni bazi.
       spodnje funkcije pa zapisujejo podatke v PB

      '''
    session = FuturesSession(max_workers=10)

    futures = []
    for api_tuple in list_of_api_requests:
            futures.append((api_tuple[0], session.get(api_tuple[1], timeout=1)))

    data = []
    for element in futures:
        try:
            data.append((element[0], element[1].result().json()))
            print('update fees OK api ', element[0])
        except Exception as e:
            data.append((element[0], 'ERROR'))
            print('read from API ERROR with:  ', element[0])

    '''
            Iterate through data and call appropriate functions, that make data clean and write it into the DB
        '''

    options = {'kucoin': updateFeesKucoin,
               'poloniex': updateFeesPoloniex,
               'bittrex': updateFeesBittrex,
               'binance' : updateFeesBinance
               }

    # connect to database
    db = connectToDatabase()

    for row in data:
        if row[1] == 'ERROR':
            continue
        else:
            fees = options[row[0]](row)
            writeToDatabase(db, row[0], fees)

    # need to take care of other exchanges, that don't have APIs for fees
    other_exchanges = {
        'bitstamp' : updateFeesBitstamp,
        'bitfinex' : updateFeesBitfinex,
        'kraken' : updateFeesKraken
    }
    for key, exchange in other_exchanges.items():
        try:
            fees = exchange()
            print('update fees OK api ', key)
            writeToDatabase(db, key, fees)

        except Exception as exc:
            print('error reading  fees ', key)
            print('Cause: ', exc)


    '''
    # check if everything is correct in db
    all = db.fees.find()
    for each in all:
        print(each)
    '''



    pass

def updateFeesKraken():
    # wire USD deposit .... https://support.kraken.com/hc/en-us/articles/201396777

    deposit_fees = {}
    deposit_fees['eur_min_abs'] = 0
    deposit_fees['eur_mid_abs'] = 0
    deposit_fees['eur_max_abs'] = 0

    deposit_fees['usd_min_abs'] = 5
    deposit_fees['usd_mid_abs'] = 5
    deposit_fees['usd_max_abs'] = 5

    '''
    r = requests.get("https://support.kraken.com/hc/en-us/articles/201893608-What-are-the-withdrawal-fees")

    data = r.text
    soup = BeautifulSoup(data, 'lxml')
    all_data = soup.findAll('ul')


    which_ul = 0
    withdrawal_fees = {}
    print(all_data)
    for row in all_data:
        if which_ul == 1:
            # data we need is here
            fee_data = row.findAll('li')
            for coin in fee_data:
                splitted_coin_data = coin.text.strip().split('-')
                coin_name = splitted_coin_data[0].split(' ')[-2][1:-1]
                if coin_name[0].islower(): # dash instant...omitted. Only DASH
                    continue

                coin_withdrawal_fee = re.findall(r"[0-9.]+", splitted_coin_data[1])
                #print(coin_withdrawal_fee)
                withdrawal_fees[coin_name] = float(coin_withdrawal_fee[0])

        which_ul += 1
    '''
    withdrawal_fees = {
        'BTC':0.0005,
        'LTC':0.001,
        'XDG':2,
        'XRP': 0.02,
        'XLM': 0.00002,
        'ETH': 0.005,
        'ETC': 0.005,
        'MLN': 0.003,
        'XMR': 0.05,
        'REP': 0.01,
        'ICN': 0.2,
        'ZEC': 0.0001,
        'DASH': 0.005,
        'GNO': 0.01,
        'USDT': 5,
        'EOS': 0.05,
        'BCH': 0.0001
    }
    # we have them set globally
    exchange_fees = {}
    exchange_fees['maker'] = KRAKEN_fee_maker
    exchange_fees['taker'] = KRAKEN_fee_taker

    fees = {}
    fees['deposit'] = deposit_fees
    fees['withdraw'] = withdrawal_fees
    fees['exchange'] = exchange_fees
    return fees
def updateFeesBitstamp():
    #  https://www.bitstamp.net/fee_schedule/

    # fees are stored as: min, mid, max ---- minimum fee, medium fee and maximum fee

    deposit_fees = {}
    deposit_fees['eur_min_abs'] = 0
    deposit_fees['eur_mid_abs'] = 0
    deposit_fees['eur_max_abs'] = 0

    deposit_fees['credit_card_%'] = 5

    deposit_fees['usd_min_abs'] = 7.5
    deposit_fees['usd_mid_%'] = 0.05
    deposit_fees['usd_max_abs'] = 300


    # all coin withdraws are free
    withdrawal_fees = {}
    for currency in ['BTC', 'ETH', 'BCH', 'XRP', 'LTC']:
        withdrawal_fees[currency] = 0

    exchange_fees = {}
    exchange_fees['maker'] = BITSTAMP_fee_maker
    exchange_fees['taker'] = BITSTAMP_fee_taker

    fees = {}
    fees['deposit'] = deposit_fees
    fees['withdraw'] = withdrawal_fees
    fees['exchange'] = exchange_fees
    return fees

def updateFeesBitfinex():
    '''
    Get fees at Bitfinex. Web scraping the 'fees' page on their website.

    :return: insert into database
    '''
    # https://www.bitfinex.com/fees

    bank_deposit = (20, 0.001) # minimum 20 EUR/USD, else 0.1 %

    # abs is absoulte value in eur or usd. % is percent value from total deposit
    deposit_fees = {}
    deposit_fees['eur_min_abs'] = 20
    deposit_fees['eur_mid_%'] = 0.1
    deposit_fees['eur_max_%'] = 0.1

    deposit_fees['usd_min_abs'] = 20
    deposit_fees['usd_mid_%'] = 0.1
    deposit_fees['usd_max_%'] = 0.1


    r = requests.get("https://www.bitfinex.com/fees")

    data = r.text
    soup = BeautifulSoup(data, "lxml")

    # getting and matching the withdrawal fees
    fee_data = soup.findAll('td', {'class': 'bfx-green-text col-info'})

    start_scraping = 0 # when the values equals 2 we start scraping. Reason: depost fees are first, then are withdrawals
    pass_first_usd = 0 # we pass first usd - USD OMNI withdraw - wut

    withdrawal_fees = {}
    # iterate through the table with fees on their website
    for row in fee_data:
        fee = str(row.text.strip())
        try:
            if fee.split(' ')[1] == 'BTC':
                start_scraping += 1
        except Exception as exc:
            pass
        if start_scraping == 2:
            try:
                fee = fee.split(' ')
                if pass_first_usd > 0 and fee[1] == 'USD':
                    currency = 'USDT'
                    rate = fee[0]
                    withdrawal_fees[currency] = float(rate)
                elif fee[1] == 'USD':
                    pass_first_usd += 1
                    continue
                elif fee[1] == 'EUR': # EURT...no
                    continue
                elif fee[1][0] == '(':
                    continue
                else:
                    currency = fee[1]
                    rate = fee[0]
                    withdrawal_fees[currency] = float(rate)
            except Exception as exc:
                continue

    # some coins are free to withdraw. Hard to scrape them. Add them.
    for free_withdraw_coin in ['BTG', 'NEO']:
        if free_withdraw_coin in withdrawal_fees:
            continue
        else:
            withdrawal_fees[free_withdraw_coin] = 0.0


    exchange_fees = {}
    exchange_fees['maker'] = BITFINEX_fee_maker
    exchange_fees['taker'] = BITFINEX_fee_taker

    fees = {}
    fees['deposit'] = deposit_fees
    fees['withdraw'] = withdrawal_fees

    fees['exchange'] = exchange_fees

    return fees

def updateFeesBinance(data):
    '''

    :param data: data we got from API
    :return: dictionary with all the fees from this website.
    '''
    coins = data[1]

    deposit_fees = {}

    withdrawal_fees = {}
    for coin in coins:
        withdrawal_fees[coin['assetCode']] = coin['transactionFee']


    exchange_fees = {}
    exchange_fees['maker'] = BINANCE_fee_maker
    exchange_fees['taker'] = BINANCE_fee_taker

    fees = {}
    fees['deposit'] = deposit_fees
    fees['withdraw'] = withdrawal_fees

    fees['exchange'] = exchange_fees
    return fees


def updateFeesKucoin(data):
    '''

    :param data: data we got from API
    :return: dictionary with all the fees from this website.
    '''
    coins = data[1]['data']

    deposit_fees = {}


    withdrawal_fees = {}
    for coin in coins:
        withdrawal_fees[coin['coin']] = float(coin['withdrawMinFee'])

    exchange_fees = {}
    exchange_fees['maker'] = KUCOIN_fee_maker
    exchange_fees['taker'] = KUCOIN_fee_taker

    fees = {}
    fees['deposit'] = deposit_fees
    fees['withdraw'] = withdrawal_fees

    fees['exchange'] = exchange_fees

    return fees

def updateFeesPoloniex(data):
    '''

    :param data: data we got from API
    :return: dictionary with all the fees from this website.
    '''

    coins = data[1]

    deposit_fees = {}

    withdrawal_fees = {}
    for coin in coins.keys():
        # not all coins are even trading there. But we query fees based on trading pairs, so it will be ok
        withdrawal_fees[coin] = float(coins[coin]['txFee'])

    exchange_fees = {}
    exchange_fees['maker'] = POLONIEX_fee_maker
    exchange_fees['taker'] = POLONIEX_fee_taker

    fees = {}
    fees['deposit'] = deposit_fees
    fees['withdraw'] = withdrawal_fees

    fees['exchange'] = exchange_fees

    return fees


def updateFeesBittrex(data):
    '''

    :param data: data we got from API
    :return: dictionary with all the fees from this website.
    '''

    coins = data[1]['result']

    deposit_fees = {}

    withdrawal_fees = {}
    for coin in coins:
        withdrawal_fees[coin['Currency']] = float(coin['TxFee'])

    exchange_fees = {}
    exchange_fees['maker'] = BITTREX_fee_maker
    exchange_fees['taker'] = BITTREX_fee_taker

    fees = {}
    fees['deposit'] = deposit_fees
    fees['withdraw'] = withdrawal_fees

    fees['exchange'] = exchange_fees

    return fees



# This gets called from the webApp once, when we launch the web app.
'''
def updateFeesAPI():
    updateFees()
    print('sleeping for 24h')
    time.sleep(30) # once per day '24*60*60'
    updateFeesAPI()
'''