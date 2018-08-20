# Crypto Shortest Path
Application that gives you the optimal path for purchasing a specific cryptocurrency with fiat currency.

The use case for this application is figuring out, what route to take to your desired cryptocurrency. User inputs data about starting currency (EUR or USD), investment amount and target currency.

Currently supported exchanges in the application are: Bitstamp, Kraken, Bitfinex, Bittrex, KuCoin, Binance, Poloniex.



To run the application on localhost:
1. Launch mongodb database with `mongod`
2. Start Flask server using `FLASK_APP=run.py flask run`
3. Start Vue frontend by `cd frontend && npm install && npm run dev`
4. Test on `http://localhost:8090` or send GET request manually to `http://localhost:5000/shortestPath`

For production use **gunicorn** instead of Flask for running the server.
