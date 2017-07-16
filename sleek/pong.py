from flask import Flask, request
from datetime import datetime
import json
import pprint
from slackclient import SlackClient
import requests

LOG = "/tmp/foo.log"
def log_it(fname, m):
	now = datetime.now().strftime("%Y-%m-%d %H:%M")
	with open(fname,"a") as f:
		f.write("[{}]\t{}\n".format(now, m))

app = Flask(__name__) 
@app.route("/sleek",methods=['GET', 'POST'])
def sleek():			
	
	if request.method == 'POST':			
		payload = json.loads(request.form['payload'])
		user_id = payload["user"]["id"]
		survey_id = payload["callback_id"]
		q_id = payload["actions"][0]["name"]
		ans = payload["actions"][0]["value"]
		response = {q_id:ans}
		ts = datetime.now().strftime('%Y-%m-%d %H:%M')
		response["ts"]=ts
		thread_ts = payload["message_ts"]		
		log_it(LOG, pprint.pformat(payload, indent=3)) 
		requests.post(payload["response_url"], data = {'text':'hello'})		
		return "sidekick ok"		
	else:
		return "Gotta get it on"

@app.route("/",methods=['GET'])
def hello():			
	return "Hi there! :)"

if __name__ == "__main__": 
	app.run()
