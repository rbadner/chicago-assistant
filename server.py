import urllib
import json
import os
from flask import Flask
from flask import request
from flask import make_response

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
	req = request.get_json(silent = True, force = True)
	print('Request:\n', json.dumps(req, indent=4))
	res = makeWebhookResult(req)
	res = json.dumps(res, indent=4)
	print(res)
	r = make_response(res)
	r.headers['Content-Type'] = 'application/json'
	
	return r

@app.route('/', methods=['GET'])
def hello():
	return "Hello World!"
# def makeWebhokResult(req):
# 	pri

def makeWebhookResult(req):
	speech = "Hi, Vidal!"
	return {
		'speech': speech,
		'displayText': speech,
		'source': 'Vidal\'s Mind'
	}


if __name__ == '__main__':
	app.run(debug=True)