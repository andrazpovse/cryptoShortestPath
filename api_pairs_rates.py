
from requests_futures.sessions import FuturesSession
import time
from pymongo import MongoClient


# list with tuples - (exchange name, API URL)
list_of_api_requests = [
    ('kucoin', "https://api.kucoin.com/v1/market/open/symbols"),

    ('poloniex', "https://poloniex.com/public?command=returnTicker"),

    ('binance', "https://api.binance.com/api/v3/ticker/price"),

    ('coinmarketcap', "https://api.coinmarketcap.com/v1/ticker/?limit=500"),

    ('bitstamp', "https://www.bitstamp.net/api/v2/trading-pairs-info/"),

    ('bitfinex', "https://api.bitfinex.com/v1/symbols"),

    ('bittrex', "https://bittrex.com/api/v1.1/public/getmarketsummaries"),

   # ('hitbtc', "https://api.hitbtc.com/api/2/public/ticker"), # currently not using. Public data about withdraw fees not there.

    ('kraken', "https://api.kraken.com/0/public/AssetPairs"),

    ('eur_usd', 'http://free.currencyconverterapi.com/api/v5/convert?q=EUR_USD&compact=y')
]


def connectToDatabase():
    # Naredimo ustrezne strukture v MongoDB
    client = MongoClient('localhost', 27017)
    # ustvari bazo z imenom (ce se ne obstaja)
    db = client['database']



    return db

def updateAPIvalues():
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
            print('update pairs OK ', element[0])
        except Exception as e:
            data.append((element[0], 'ERROR'))
            print('update pairs ERROR with ', element[0])

    '''
        Iterate through data and call appropriate functions, that make data clean and write it into the DB
    '''

    options = {'kucoin': getPairsAndPricesAtKuCoin,
               'poloniex': getPairsAndPricesAtPoloniex,
               'coinmarketcap': getCoinMarketCapPrices,
               'bitstamp': getPairsAndPricesAtBitstamp,
               'bitfinex': getPairsAndPricesAtBitfinex,
               'binance': getPairsAndPricesAtBinance,
               'bittrex': getPairsAndPricesAtBittrex,
               #'hitbtc': getPairsAndPricesAtHitBtc,
               'kraken': getPairsAndPricesAtKraken,
               'eur_usd': getEurToUsdRate
               }


    # maybe a try catch here
    insert_into_db = {} # dictionary with key - name of exchange, values - dict of pairs, rates, ...
    db = connectToDatabase()
    for row in data:
        if row[1] == 'ERROR':
            continue
        else:
            # coinmarketcap doesnt have pairs, but prices of each coin. Dictionary, keys = symbols, values = tuple(usd, btc price)
            insert_into_db = {}
            pairs_at = options[row[0]](row)
            # update documents
            db.rates.update_one({ 'name': row[0]}, { '$set': { 'time': time.time(), 'data': pairs_at}}, upsert=True)


def getEurToUsdRate(api_data):
    '''

    :param api_data: Tuple (pair name, json response)
    :return: dict with rate
    '''
    rate = {
        'rate' : api_data[1]['EUR_USD']['val']
    }
    return rate


def getPairsAndPricesAtKuCoin(api_data):
    '''

    :param api_data: Tuple (exchange name, json response)
    :return: pairs and their prices. Dictonary keys are tradable pairs, values are dicts 'paired currency : trading price'
    '''

    data = api_data[1]['data']

    prices_at_kucoin = {}
    for item in data:
        try:
            prices_at_kucoin.setdefault(item['symbol'].split("-")[1], {}).update({(item['symbol'].split('-'))[0]: float(item['lastDealPrice'])})
        except Exception as exc:
            continue # new coin, not trading yet i suppose



    return prices_at_kucoin

def getPairsAndPricesAtPoloniex(api_data):
    '''

    :param api_data: Tuple (exchange name, json response)
    :return: pairs and their prices. Dictonary keys are tradable pairs, values are dicts 'paired currency : trading price'
    '''

    data = api_data[1]

    prices_at_poloniex = {}
    for key in data.keys():
        prices_at_poloniex.setdefault(key.split("_")[0], {}).update({key.split("_")[1] :  float(data[key]['last'])})
    return prices_at_poloniex

def getPairsAndPricesAtBinance(api_data):
    '''

    :param api_data: Tuple (exchange name, json response)
    :return: pairs and their prices. Dictonary keys are tradable pairs, values are dicts 'paired currency : trading price'
    '''

    data = api_data[1]
    prices_at_binance = {} # tuples (pair, price)
    for coin in data:
        if coin['symbol'] == '123456':
            # problem with Binance's API
            continue
        currency = coin['symbol'][-3:]
        # they have poor method of displaying pairs...hence hard split
        if currency == 'SDT':
            currency = 'USDT'
        prices_at_binance.setdefault(currency, {}).update({coin['symbol'][0:-3] : float(coin['price'])})

    return prices_at_binance



def getPairsAndPricesAtBitstamp(api_data):
    '''

    :return: pairs and their prices. Dictonary keys are tradable pairs, values are dicts 'paired currency : trading price'
    '''
    data = api_data[1]

    session = FuturesSession(max_workers=10)


    # bitstamp only returns pairs. Need to get their last prices with API call for each pair
    list_of_api_requests = []
    for pair in data:
        pair_names = pair['name'].split('/')
        list_of_api_requests.append('https://www.bitstamp.net/api/v2/ticker/'+pair_names[0].lower()+''+pair_names[1].lower())

    # we do it in parallel
    futures = []
    for api_link in list_of_api_requests:
        futures.append(session.get(api_link, timeout=1))

    trading_data = []
    for element in futures:
        try:
            trading_data.append(element.result().json())
        except Exception as e:
            print('ERROR - bitstamp ', e)

    # we have pairs and prices now. Zip them together and add them into a dictionary.
    prices_at_bitstamp = {}
    for pairs, trades in zip(data, trading_data):
        prices_at_bitstamp.setdefault(pairs['name'].split("/")[1], {}).update(
            { (pairs['name'].split('/'))[0] : float(trades['last'])})


    # this dictionary will be written into DB.
    #print(prices_at_bitstamp)
    return prices_at_bitstamp






def getPairsAndPricesAtBitfinex(api_data):
    '''

    :return: pairs and their prices. Dictonary keys are tradable pairs, values are dicts 'paired currency : trading price'
    '''


    # "https://api.bitfinex.com/v1/symbols"
    # 'https://api.bitfinex.com/v1/pubticker/zecbtc'
    data = api_data[1]


    # Make string of all symbols. You want last price of all trading pairs
    string_of_symbols = ''
    for pair in data:
        string_of_symbols += 't'+pair.upper()+','

    # removes last symbol -  ','
    string_of_symbols = string_of_symbols[:-1]
    # print(string_of_symbols)

    # send API request
    session = FuturesSession()
    future = session.get('https://api.bitfinex.com/v2/tickers?symbols='+string_of_symbols)
    result = future.result().json()

    # Make dict like everywhere else
    prices_at_bitfinex = {}
    for pair in result:
        currency_one = pair[0][-3:] # tBTCUSD....currency_one = USD
        currency_two = pair[0][1:-3] # currency_two = BTC
        if (currency_two == 'IOT'):
            currency_two = 'MIOTA'
        if (currency_two == 'QTM'):
            currency_two = 'QTUM'
        if (currency_two == 'MIT'):
            currency_two = 'MITH'
        prices_at_bitfinex.setdefault(currency_one, {}).update(
            {currency_two : float(pair[7])})
    # print(prices_at_bitfinex)

    return prices_at_bitfinex



def getPairsAndPricesAtBittrex(api_data):
    '''

    :return:  pairs and their prices. Dictonary keys are tradable pairs, values are dicts 'paired currency : trading price'
    '''

    data = api_data[1]['result']

    prices_at_bittrex = {}  # tuples (pair, price)
    for coin in data:
        prices_at_bittrex.setdefault(coin['MarketName'].split('-')[0], {}).update(
            {coin['MarketName'].split('-')[1] : float(coin['Last'])})


    '''
    # Tako dobimo mnozice valut, ki se menjajo s katerim parom.
    
    a = set(i[0] for i in prices_at_bittrex['BTC'])
    b = set(i[0] for i in prices_at_bittrex['ETH'])
    c = set(i[0] for i in prices_at_bittrex['USDT'])

    print(a.intersection(b))
    '''
    return prices_at_bittrex



def getPairsAndPricesAtHitBtc(api_data):
    '''

    :return: pairs and their prices. Dictonary keys are tradable pairs, values are dicts 'paired currency : trading price'
    '''
    data = api_data[1]

    prices_at_hitbtc = {}  # tuples (pair, price)
    for coin in data:
        try:
            trading_pair = coin['symbol'][-3:] # Same as Binance...hard split - ETHBTC, ETHUSDT....
            if trading_pair == 'SDT':
                trading_pair = 'USDT'

            prices_at_hitbtc.setdefault(trading_pair, {}).update(
                {coin['symbol'][0:-3] : float(coin['last'])})
        except Exception as exc:
            continue # probably new coin, not trading yet

    #print(prices_at_hitbtc.keys())
    return prices_at_hitbtc




def getPairsAndPricesAtKraken(api_data):
    '''

    :param api_data:
    :return: pairs and their prices. Dictonary keys are tradable pairs, values are dicts 'paired currency : trading price'
    '''

    data = api_data[1]['result']

    # Make string of all symbols. You want last price of all trading pairs
    string_of_symbols = ''
    for pair in data:
        if pair[-1] != 'd':
            string_of_symbols += pair.upper() + ','

    # removes last symbol -  ','
    string_of_symbols = string_of_symbols[:-1]
    # print(string_of_symbols)

    # send API request
    session = FuturesSession()
    future = session.get('https://api.kraken.com/0/public/Ticker?pair=' + string_of_symbols)
    result = future.result().json()['result']

    prices_at_kraken = {}  # tuples (pair, price)
    for pair in result:
        try:
            trading_pair = pair[-3:] # Same as Binance...hard split - ETHBTC, ETHUSDT....
            base_pair = pair[0:-3]


            # Weird returned pairs, like XETHZ...needs to be filtered. BTC also named as XBT, so needs renaming

            if base_pair[0] == 'X':
                base_pair = base_pair[1:]
            if base_pair[-1] =='Z' or base_pair[-1] == 'X':
                base_pair = base_pair[:-1]

            if trading_pair == 'SDT':
                trading_pair = 'USDT'
            if trading_pair == 'XBT':
                trading_pair = 'BTC'
            if base_pair == 'XBT':
                base_pair = 'BTC'
            if base_pair == 'SDT':
                base_pair = 'USDT'

            prices_at_kraken.setdefault(trading_pair, {}).update(
                {base_pair : float(result[pair]['c'][0])})
        except Exception as exc:
            continue # probably new coin, not trading yet

    return prices_at_kraken


''' Maybe include prices of coins in some different place
    Different placement in the database, not along pairs and rates
    
    connect to db here and modify data? Maybe even seperate file.
'''
def getCoinMarketCapPrices(api_data):
    '''

    :param api_data: Tuple (name, json response)
    :return: pairs and their prices. Dictonary keys are tradable pairs, values are dicts 'paired currency : trading price'
    '''
    data = api_data[1]
    coinmarketcap_prices = {}
    for coin in data:
        currency = coin['symbol'][-3:]
        if (coin['symbol'][0] == '$'):
            continue
        else:
            coinmarketcap_prices[coin['symbol']] = (coin['price_usd'], coin['price_btc'])


    return coinmarketcap_prices




# This gets called from the webApp once, when we launch the web app.
'''
def updatePairsAPI():
    updateAPIvalues()
    print('sleeping for 5 minutes')
    time.sleep(20) # once per 5 minutes 5*60
    updatePairsAPI()
'''

#updatePairsAPI()



