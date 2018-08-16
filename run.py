from flask import Flask, render_template, request
from random import *
import json
from flask_cors import CORS
import gatewayForAPIs
# Import shortest path function
import cheapest_path

app = Flask(__name__, static_folder = "./dist/static", template_folder = "./dist")
cors = CORS(app)
        

@app.route('/shortestPath', methods=['GET'])
def shortestPath():
    error = ''
    try:
        # Call shortest path function with arguments here
        path_startValue_endValue_endCount = cheapest_path.cheapestPathAPI(request.args.get('currency'),request.args.get('targetCrypto'),float(request.args.get('investedAmount')))
        valueStart = str(path_startValue_endValue_endCount[1]) + ' USD'
        endValue = str(path_startValue_endValue_endCount[2]) + ' USD'
        amount = str(path_startValue_endValue_endCount[3]) + ' ' + str(request.args.get('targetCrypto')).upper()
        path = path_startValue_endValue_endCount[0]
    except Exception as e:
        print(e)
        error = 'Prišlo je do napake. Ponovno preizkusite kasneje.'
        amount = '/'
        valueStart = '/'
        endValue = '/'
        path=''
    response = {
        'amount': amount,
        'startValue': valueStart,
        'endValue': endValue,
        'shortestPath': path,
        'error': error
    }
    return json.dumps(response)
    
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return render_template("index.html")


