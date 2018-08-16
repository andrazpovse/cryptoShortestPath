from pymongo import MongoClient
from collections import defaultdict
import pylab as plt

import networkx as nx

# do it, do the network



# for mongodb connection
def connectToDatabase():
    '''

    :return: connection to database
    '''
    client = MongoClient('localhost', 27017)
    db = client['database']

    return db


def getFeesFromDatabase():
    '''

    :return: list of dictionaries. All the included exchanges. Each dictionary has 'name' of the exchange,
    'time' at which it was updated and 'data' which includes all deposit and withdraw fees for coins/fiat.

    Fees are available at collection 'fees' in mongodb client 'database'
    '''
    db = connectToDatabase()

    # print('fees from database')
    all = db.fees.find()
    return_list = []
    for each in all:
        # print(each)
        return_list.append(each)

    return return_list

def getPairsFromDatabase():
    '''

    :return: list of dictionaries. All the included exchanges. Each dictionary has 'name' of the exchange,
    'time' at which it was updated and 'data' which includes all the trading pairs.
    '''
    db = connectToDatabase()
    all = db.rates.find()

    # Makes a dictionary of all exchanges. Keys are names.
    exchanges = {}

    for exchange in all:
        exchanges[exchange['name']] = exchange

    return exchanges

def getCoinmarketcapPricesUSD(coinmarketcap_info):
    '''

    :param coinmarketcap_info: Dictionary of coins and their prices in btc and usd
    :return:  Dictionary of coins and their USD prices.
    '''
    prices={}
    for cryptocurrency, price in coinmarketcap_info.items():
        prices[cryptocurrency] = price[0] # 0 is USD, 1 is in BTC
    return prices

def get_fee(amount,fee_size, fee_type):
    '''

    :param amount: invested amount
    :param fee_size: size of fee. Unknown if in % or absolute value
    :param fee_type: either 'abs' or '%'
    :return: paid fee in absolute value
    '''

    # fee size is stored in percents. We need to further divide by 10
    if fee_type == '%':
        return amount * fee_size / 10
    else:
        return fee_size


def get_deposit_fees_fiat(fees, have_fiat_deposits, currency, invested_amount):
    '''

    :param fees: fees from database
    :param have_fiat_deposits: list of exhanges, that have fiat deposits
    :param currency: either 'usd' or 'eur'
    :param invested_amount: amount in deposit
    :return: dictionary of actual deposit fees we would pay on exchanges
    '''

    deposit_fees_fiat = {}
    for exchange in fees:
        if exchange['name'] in have_fiat_deposits:
            deposit_fees = exchange['data']['deposit']
            # print(exchange['data']['exchange'])

            min_mid_max = [] # all fees are saved in min[0], mid[1] and max[2]
            # inside are tuples, with (value, 0 or 1). '%' means it is in %, 'abs' means it is absolute

            for key, value in deposit_fees.items():
                splitted_key = key.split('_')
                if splitted_key[0] == currency:
                    min_mid_max.append((value, splitted_key[2]))
            if min_mid_max[0][0] == min_mid_max[1][0] == min_mid_max[2][0]:
                deposit_fees_fiat[exchange['name']] = min_mid_max[0][0]
            else:
                min_fee = get_fee(invested_amount, min_mid_max[0][0], min_mid_max[0][1])
                mid_fee = get_fee(invested_amount, min_mid_max[1][0], min_mid_max[1][1])
                max_fee = get_fee(invested_amount, min_mid_max[2][0], min_mid_max[2][1])

                # if maximum fee is in absolute value
                if min_mid_max[2][1] == 'abs': # bitstamp - max is 300 abs. Kraken has 5 always.
                    if max_fee < mid_fee:
                        deposit_fees_fiat[exchange['name']] = max_fee
                        continue
                if min_mid_max[1][1] == '%': # bitfinex - mid and max are 0.1%
                    # if minimum fee is less than medium fee, we pay the medium fee. Else pay minimum
                    if min_fee < mid_fee:
                        deposit_fees_fiat[exchange['name']] = mid_fee
                    else:
                        deposit_fees_fiat[exchange['name']] = min_fee


    return deposit_fees_fiat



def createFirstFiatDepositNodes(starting_currency, investment_amount, exchange_fees, deposit_fees_fiat, eur_to_usd_rate):
    '''

    :param starting_currency: eur or usd
    :param investment_amount: integer
    :param exchange_fees: dictionary of exchange fees on all exchanges
    :param deposit_fees_fiat:  dictionary of fiat deposit fees on exchanges that have fiat deposits
    :return: Network with these nodes
    '''

    starting_currency = starting_currency.upper()

    G = nx.DiGraph(directed=True)
    G.add_node('START')
    #end node. Target currency from all goals, goes to this node with an edge weighing 0
    G.add_node('GOAL')
    for exchange, fee in deposit_fees_fiat.items():
        node_name = ''.join([exchange, '_', starting_currency])
        G.add_node(node_name, count=investment_amount - fee, exchange_fee=exchange_fees[exchange], sending_fee='fiat', value=investment_amount - fee)
        G.add_edge('START', node_name, type='s', weight=fee, exchange_rate='fiat')


    #nx.draw_networkx(G, arrows=True)
    #plt.show()

    return G
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

def createAllNodes(network, exchange_fees, withdraw_fees, all_exchange_pairs, goal_currency):
    '''
    Create all nodes for the network

    :param network: Existing network, consisted of fiat nodes.
    :param exchange_fees: Fees on each exchange.
    :param withdraw_fees:  Withdraw fees on each exchange
    :param all_exchange_pairs:  All trading pairs and their rates on exchanges
    :param goal_currency: End currency. Needs to be connected to GOAL node.
    :return: Network with all nodes.
    '''
    for exchange_name, exchange_data  in all_exchange_pairs.items():
        for pair1, pair2 in exchange_data['data'].items():
            for cryptocurrency, exchange_rate in pair2.items():
                node_name = ''.join([exchange_name, '_', cryptocurrency])
                if (node_name not in network):
                    if (cryptocurrency in withdraw_fees[exchange_name]):
                        network.add_node(node_name, count=0, exchange_fee=exchange_fees[exchange_name], sending_fee=withdraw_fees[exchange_name][cryptocurrency], value=0)
                    else : #Withdraw in this currency not supported
                        network.add_node(node_name, count=0, exchange_fee=exchange_fees[exchange_name], sending_fee='no', value=0)
                    # Add connection from any exchange that has target currency to the GOAL node. Weight 0
                    if (cryptocurrency == goal_currency):
                        network.add_edge(node_name, 'GOAL', type='s', weight=0,
                                   exchange_rate='goal')
            # Vozlisce pair1
            node_name = ''.join([exchange_name, '_', pair1])
            if (node_name not in network):
                if (pair1 in withdraw_fees[exchange_name]):
                    network.add_node(node_name, count=0, exchange_fee=exchange_fees[exchange_name],
                                     sending_fee=withdraw_fees[exchange_name][pair1], value=0)
                else:  # Withdraw in this currency not supported
                    network.add_node(node_name, count=0, exchange_fee=exchange_fees[exchange_name], sending_fee='no',
                                     value=0)
                # Add connection from any exchange that has target currency to the GOAL node.
                if (pair1 == goal_currency):
                    network.add_edge(node_name, 'GOAL', type='s', weight=0,
                                     exchange_rate='goal')


    #nx.draw_networkx(network, arrows=True)
    #plt.show()
    #print(len(network))
    return network


def createAllEdges(network, all_exchange_pairs, eur_to_usd_rate, coinmarketcap_rates):
    '''

    :param network: NetworkX network. So far it has all nodes and some connections.
    :param all_exchange_pairs: Pairs and their exchange rates. ALl exchanges
    :param eur_to_usd_rate: Exchange rate for EUR/USD pair.
    :param coinmarketcap_rates: Prices of cryptocurrencies in USD

    :return: dictionary with information about shortest path. Keys are like (edge_X or node_X, where X is number of the edge or node)
    '''



    '''
    Gledam tiste, ki imajo value
    
    Note: menjava gre lahko tudi obratno BTC/LTC --- LTC/BTC
    '''
    for _ in range(5):
        for exchange_name, exchange_data in all_exchange_pairs.items():
            for pair1, dict_of_pairs in exchange_data['data'].items():
                edge_start = ''.join([exchange_name, '_', pair1])
                # Posljem lahko na katerokoli menjalnico, vazno samo da je ista valuta ---------- type = s
                for name in network.nodes():
                    if (name == 'GOAL' or name == 'START'):  # Unordinary nodes
                        continue
                    else:
                        splitted_name = name.split('_')
                        if (splitted_name[1] == pair1):
                            if (network.node[edge_start]['sending_fee'] != 'no'):
                                if (isinstance(network.node[edge_start]['sending_fee'], int)):
                                    network.add_edge(edge_start, name, type='s',
                                                     weight=network.node[edge_start]['sending_fee']*float(coinmarketcap_rates[pair1]))
                                    if (network.node[name]['value'] < (network.node[edge_start]['value'] - network.node[edge_start]['sending_fee']* float(coinmarketcap_rates[pair1]))):
                                        network.node[name]['value'] = network.node[edge_start]['value'] - network.node[edge_start]['sending_fee'] * float(coinmarketcap_rates[pair1])
                                        network.node[name]['count'] = network.node[edge_start]['count'] - network.node[edge_start]['sending_fee']

                # Vse povezave, ki samo menjajo na isti menjalnici --------------   type = e
                if (network.node[edge_start]['value'] != 0):
                    for cryptocurrency, exchange_rate in dict_of_pairs.items():

                        edge_end = ''.join([exchange_name, '_', cryptocurrency])

                        # BTC/XRP ----------- N1.amount / exchange rate
                        #print(exchange_rate, ' ', cryptocurrency)
                        try:
                            new_amount = (float(network.node[edge_start]['count']))/exchange_rate
                            new_amount -= new_amount * network.node[edge_end]['exchange_fee'] # Minus exchange fee
                        except Exception as e:
                            print('Error with exchange rate, ', e)

                       # print(pair1, ' trades with ', cryptocurrency, ' at rate: ', exchange_rate)

                        try:
                            '''
                            if (pair1 =='EUR'):
                                new_value = new_amount * exchange_rate * eur_to_usd_rate
                            elif (pair1 == 'USD'):
                                new_value = new_amount * exchange_rate
                            elif (pair1 == 'BTC' or pair1 == 'ETH' or pair1 == 'BNB'):
                                new_value = float(coinmarketcap_rates[pair1]) * new_amount * exchange_rate

                                if (edge_end == 'binance_ETH'):
                                    print('before', network.node[edge_start]['value'], ' and count ', network.node[edge_start]['count'])
                                    print(float(coinmarketcap_rates[pair1]),  '*',  new_amount, '*', exchange_rate)
                                    print(new_value, ' new value')
                            else:
                            '''     
                            new_value = float(coinmarketcap_rates[cryptocurrency]) * new_amount
                        except Exception as e:
                            #print("type error: " + str(e))
                            continue
                        if (network.node[edge_end]['value'] < new_value):
                            network.node[edge_end]['value'] = new_value
                            network.node[edge_end]['count'] = new_amount

                        if (edge_start.split('_')[1] == 'EUR'): # eurusd exchange rate
                            weight = network.node[edge_start]['value'] * eur_to_usd_rate - new_value # weight = N1.value - N2.value
                        else:
                            weight = network.node[edge_start]['value'] - new_value

                        network.add_edge(edge_start, edge_end, type='e', weight=weight)

  
    #vsiCilji = list(network.in_edges('GOAL'));
    #for node_goal in vsiCilji:
        #print('vozlišče: ',node_goal[0], ', število ', network.node[node_goal[0]]['count'], ', vrednost', network.node[node_goal[0]]['value'])


    '''
    for cycle in cycles:
        cycle.append(cycle[0])
        sumw = sum([weights[(cycle[i - 1], cycle[i])] for i in range(1, len(cycle))])
        if (sumw < 0):
            print(cycle, ' weighted ', sumw)
    '''
    shortest_path = nx.bellman_ford_path(network, 'START', 'GOAL')
    #print(shortest_path)

    # TODO..... make this function return shortest path with information about:
    '''
        Node name (maybe split into: exchange name, cryptocurrency name)
        Value inside node (in USD)
        Count inside node
        
        Each edge weight and type (?)
        
        Total path cost
    '''
    shortestPathInformationDict = {}
    counter = 0
    for name in shortest_path:
        splittedName = name.split('_')
        print(splittedName)
        key = 'node_'+ str(counter)
        if (name != 'START' and name != 'GOAL'):
            shortestPathInformationDict[key] = network.node[name]
            shortestPathInformationDict[key]['node_name'] = name
            shortestPathInformationDict[key]['exchange_name'] = splittedName[0]
            shortestPathInformationDict[key]['currency'] = splittedName[1]
        if (counter >= 1 and counter < len(shortest_path)-1):
            #print(counter, '  ...///...  ', len(shortest_path))
            key = 'edge_' + str(counter)
            shortestPathInformationDict[key] = network[previousName][name]
            #print(network[previousName][name])
        #print(network.node[name])
        previousName = name
        counter += 1
    #print(shortestPathInformationDict)

    endValue = network.node[shortest_path[-2]]['value']
    endCount = network.node[shortest_path[-2]]['count']



    return shortestPathInformationDict, endValue, endCount


#Request from front end calls at about this place. Wrap this in a function

def findShortestPath(starting_currency, goal_currency, investment_amount):
    # List of exchanges that have FIAT depossit available.
    have_fiat_deposits = ['kraken', 'bitstamp', 'bitfinex']
    buy_order = 'taker' # taker or maker

    '''
    Calls for data in the database
    '''
    pairs = getPairsFromDatabase() # Get dictionary with information on pairs in exchanges.
    fees = getFeesFromDatabase() # Get JSON object with dict with fees from exchanges
    exchange_fees = {} # Fees when exchanging one crpyo for another
    cryptocurrency_prices_usd = getCoinmarketcapPricesUSD(pairs['coinmarketcap']['data']) # We will calculate fees and other things in USD
    eur_to_usd_rate = pairs['eur_usd']['data']['rate']
    print('if in eur, to usd', investment_amount*eur_to_usd_rate)


    pairs.pop('eur_usd', None) # ne rabimo pri gradnji
    pairs.pop('coinmarketcap', None) # ne rabimo pri gradnji

    withdraw_fees = defaultdict(dict) # Fees when withdrawing cryptocurrency from an exchange
    # keys are exchanges, values fees (NOT IN %, but in rate). We picked if they are maker or taker from parameters above
    for exchange in fees:
        exchange_fees[exchange['name']] = exchange['data']['exchange'][buy_order]
        for withdraw_currency, withdraw_fee in exchange['data']['withdraw'].items():
            withdraw_fees[exchange['name']][withdraw_currency] = withdraw_fee
    # deposit fee is the fee the user will pay, to get fiat funds on the exchange
    deposit_fees_fiat = get_deposit_fees_fiat(fees, have_fiat_deposits, starting_currency, investment_amount)


    '''
    Create network. First make the starting nodes and all other that accept FIAT deposits.
    '''
    #Make first nodes[as much as there are exchanges with fiat deposits], that just take deposit fee into account.
    network = createFirstFiatDepositNodes(starting_currency, investment_amount, exchange_fees, deposit_fees_fiat, eur_to_usd_rate)

    # Create all nodes in the graph
    network = createAllNodes(network, exchange_fees, withdraw_fees, pairs, goal_currency.upper())

    #create all edges and return shortest path and all goals

    shortest_path, endValue, endCount = createAllEdges(network, pairs, eur_to_usd_rate, cryptocurrency_prices_usd)


    if (starting_currency == 'eur'):
        starting_value = investment_amount * eur_to_usd_rate
    else:
        starting_value = investment_amount

    return (shortest_path, starting_value, endValue, endCount)





'''
This comes from web request. Starting currency, goal cryptocurrency and investment amount
'''
starting_currency = 'usd'
goal_currency = 'kcs'
investment_amount = 500


def cheapestPathAPI(starting_currency, goal_currency, investment_amount):
    shortest_path_dict, starting_value, endValue, endCount = findShortestPath(starting_currency, goal_currency, investment_amount)


    return (shortest_path_dict, starting_value, endValue, endCount)

#print(cheapestPathAPI(starting_currency, goal_currency, investment_amount))