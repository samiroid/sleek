from datetime import datetime
from flask import Flask, request
import json
import os
import pprint
from pdb import set_trace
from slackclient import SlackClient
import sys

LOG = "/tmp/foo.log"
confs = "pongconf.txt"
api_tokens = {}

def get_api_token(key, method="env"):
	if method == "env":
		return os.getenv(key)	
	else:
		raise NotImplementedError, "method {} unknwown".format(method)

def load_tokens():
	with open(confs) as f:
		f.next()
		for l in f:		
			if len(l) == 0: continue
			cf = l.split(",")
			if len(cf) != 3: 
				sys.stderr.write("ignored line: {}\n".format(l))	
				continue
			team, method, key = cf
			key = key.replace("\n","")
			if method == "None":
				api_tokens[team] = key
			else:
				token = get_api_token(key, method)
				if token is not None:
					api_tokens[team] = token
				else:
					sys.stderr.write("could not find token with key: {}\n".format(key))

def log_it(fname, m):
	now = datetime.now().strftime("%Y-%m-%d %H:%M")
	with open(fname,"a") as f:
		f.write("[{}]\t{}\n".format(now, m))

app = Flask(__name__) 
@app.route("/sleek",methods=['GET', 'POST'])
def sleek():				
	if request.method == 'POST':			
		payload = json.loads(request.form['payload'])		
		pprint.pprint(payload)
		bot = payload["original_message"]["user"]
		slack_user, api_token = payload["callback_id"].split("@")		
		thread_ts = payload["original_message"]["ts"]
		action = payload['actions'][0]		
		question = action["name"]
		ans      = action["value"] 		
		txt = question + " " + ans				
		key = payload["team"]["domain"]
		print "key: {}".format(key)
		# slacker = SlackClient(api_tokens[key])
		slacker = SlackClient(api_token)
		attach = []
		attach.append({ "fallback": "pong",
        		 		"text": txt,
        		 		"author_name": slack_user,        		 		
		  				})
		slacker.api_call("chat.postMessage",
	  					 channel=bot,
	  					 as_user=True,	  	
	  					 text="pong",
	  					 attachments=attach,
	  					 thread_ts=thread_ts)
		return ""
	else:
		return "pong get :)"

@app.route("/",methods=['GET'])
def hello():			
	return "Hi there! :)"

# load_tokens()
# if len(api_tokens) == 0: raise RuntimeError
# sys.stderr.write(repr(api_tokens))

if __name__ == "__main__": 
	app.run()
