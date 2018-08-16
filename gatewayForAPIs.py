from threading import Thread
import time

# Import the files
import api_pairs_rates
import api_fees

def callApiFees():
    api_fees.updateFees()
    print('Fee calling sleeping for 24h')
    time.sleep(24*60*60)  # once per day '24*60*60'
    callApiFees()

def callApiPairs():
    api_pairs_rates.updateAPIvalues()
    print('Pairs rates sleeping for 5 minutes')
    time.sleep(5*60)  # once per 5 minutes 5*60
    callApiPairs()


Thread(target = callApiFees).start()
Thread(target = callApiPairs).start()
