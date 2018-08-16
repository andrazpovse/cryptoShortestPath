
<style type="text/css">
  @import '../../node_modules/vis/dist/vis.css';
  #mynetwork {
      margin-top: -20%;
      height: 700px;
      width: 350px;
      border: 1px solid lightgray;
      margin: left;
  }
</style>

<template>
  <div style='width: 100%'>
    <div style='width: 50%; float:right;'>
     <div id="mynetwork"></div>
    </div>
    <div style='width: 50%; float:left; margin-top: 50px;'>
      <form id="signup-form" @submit.prevent="sendRequest">

        <div class="field">
          <label class="label">Začetna valuta: </label>
          <select v-model='currency' required>
            <option value="usd">USD</option>
            <option value="eur">EUR</option>
          </select>
        </div>

        <div class="field">
          <label class="label">Količina: </label>
          <input type="text" class="input"  v-model="investedAmount" required>
        </div>

        <div class="field">
          <label class="label">Ciljna kriptovaluta: </label>
          <input type="text" class="input" v-model="targetCrypto" required>
        </div>

        <!-- submit button -->
        <div class="field has-text-right">
          <button type="submit" >Izračunaj optimalno pot</button>
        </div>
      </form>
     <br> <b>{{error}}</b> <br>
      <span v-if='startValue != "" && error == ""'>
        <b>Začetna vrednost:</b> {{startValue}} <br><br>
        <b>Končna vrednost:</b> {{gotValue}}<br>
        <b>Število ciljne kriptovalute:</b> {{gotAmount}}<br><br><br><br>
        <h2> <b>Razlika končnega stanja: </b> <div v-html="profitOrLoss"></div> </h2><br>
        <br>
      </span>
    </div>
  </div>
</template>
<script>
import axios from 'axios'
import vis from 'vis'

export default {
  data () {
    return {
      network: null,
      nodes: [],
      edges: [],
      options: {interaction: {zoomView: false}, physics: {enabled: false}, layout: {hierarchical: {enabled: true, nodeSpacing: 600, direction: 'UD'}}},
      container: '',
      randomNumber: 0,
      currency: 'usd',
      investedAmount: '500',
      targetCrypto: 'BTC',
      gotValue: '',
      gotAmount: '',
      startValue: '',
      error: '',
      shortestPath: '',
      profitOrLoss: ''
    }
  },
  methods: {
    sendRequest: function () {
      axios({
        method: 'get',
        url: `http://localhost:5000/shortestPath`,
        params: {
          currency: this.currency,
          investedAmount: this.investedAmount,
          targetCrypto: this.targetCrypto
        },
        headers: {'Access-Control-Allow-Origin': '*'}
      }).then(response => {
        this.gotValue = parseFloat(response.data['endValue']).toFixed(2) + ' USD'
        this.gotAmount = response.data['amount']
        this.startValue = response.data['startValue']
        this.shortestPath = response.data['shortestPath']
        this.createGraph(this.shortestPath)
        this.error = response.data['error']
        // console.log(response)
      })
        .catch(error => {
          console.log(error)
        })
    },
    createGraph: function (shortestPathDict) {
      // clear graph
      this.edges = []
      this.nodes = []
      // start node
      this.nodes.push({id: 1, font: {color: 'white'}, label: 'START_' + this.currency.toUpperCase(), size: 80, shape: 'circle', title: 'Beginning node', color: 'red'})
      // Build nodes based on the dictionary
      var valueCurrency = ''
      for (var key in shortestPathDict) {
        var splitKey = key.split('_')
        var type = splitKey[0] // node or edge
        var id = parseInt(splitKey[1])
        if (type === 'node') {
          id += 1
          if (shortestPathDict[key]['currency'] === 'EUR') {
            valueCurrency = 'EUR'
          } else {
            valueCurrency = 'USD'
          }
          var title = '<ul>'
          title += '<li> <b> Ime menjalnice: </b>' + shortestPathDict[key]['exchange_name'] + '</li>'
          title += '<li> <b> Valuta: </b>' + shortestPathDict[key]['currency'] + '</li>'
          title += '<li> <b> Število: </b>' + shortestPathDict[key]['count'] + ' ' + shortestPathDict[key]['currency'] + '</li>'
          title += '<li> <b> Vrednost: </b>' + shortestPathDict[key]['value'].toFixed(2) + ' ' + valueCurrency + '</li>'
          title += '</ul>'
          this.nodes.push({id: id, font: {color: 'white'}, color: 'rgb(4,161,255)', shape: 'circle', size: 80, label: shortestPathDict[key]['node_name'], title: title})
        }
      }
      // build edges
      var ctr = 1
      for (key in shortestPathDict) {
        splitKey = key.split('_')
        type = splitKey[0]
        if (type === 'edge') {
          var cost = shortestPathDict[key]['weight'].toFixed(2)
          if (cost < 0) {
            cost = Math.abs(cost)
          } else if (cost > 0) {
            cost = '-' + cost
          }
          if (shortestPathDict[key]['type'] === 's') {
            cost = 'Weight: ' + cost + ' USD'
          } else {
            cost = 'Weight: ' + cost + ' USD'
          }
          this.edges.push({from: ctr, to: ctr + 1, arrows: 'to', label: cost, length: 300})
          ctr += 1
        }
      }
      var profitLoss = parseFloat(this.gotValue) - parseFloat(this.startValue)
      if (profitLoss >= 0) {
        this.profitOrLoss = '<font color="green">' + (profitLoss).toFixed(2) + ' $</font>'
      } else {
        this.profitOrLoss = '<font color="red">' + (profitLoss).toFixed(2) + ' $</font>'
      }
      this.refreshNetwork()
    },
    refreshNetwork: function () {
      this.container = document.getElementById('mynetwork')
      var data = {
        nodes: this.nodes,
        edges: this.edges
      }
      this.network = new vis.Network(this.container, data, this.options)
    }
  },
  mounted () {
    this.container = document.getElementById('mynetwork')
    var data = {
      nodes: this.nodes,
      edges: this.edges
    }
    this.network = new vis.Network(this.container, data, this.options)
  }

}

</script>
