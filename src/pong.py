from datetime import datetime
from flask import Flask, request
import json
import pprint
from slackclient import SlackClient
import quinn.loqsmith as loqsmith
import os
import sys

try:
	from ipdb import set_trace
except ImportError:
	from pdb import set_trace


LOG = "/tmp/foo.log"
api_tokens = {}

def get_api_token(key, method="env"):
	if method == "env":
		return os.getenv(key)
	elif method == "loqsmith":
		tok = loqsmith.get_token(key)	
		return tok.oauth_token.access_token
	else:
		raise NotImplementedError, "method {} unknwown".format(method)

def load_tokens():
	with open("pongconf.txt") as f:
		f.next()
		for l in f:			
			cf = l.split(",")
			if len(cf) != 3: 
				sys.stderr.write("ignored line: {}\n".format(l))	
				continue
			team, method, key = cf
			if method == "None":
				api_tokens[team] = key.replace("\n","")
			else:
				api_tokens[team] = get_api_token(key, method)

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
		bot_user = payload["original_message"]["user"]
		thread_ts = payload["original_message"]["thread_ts"]
		action = payload['actions'][0]		
		question = action["name"]
		ans      = action["value"] 		
		txt = question + " " + ans		
		key = payload["team"]["domain"]
		print "key: {}".format(key)
		slacker = SlackClient(api_tokens[key])
		attach = []
		attach.append({ "fallback": "notes",
        		 		"text": txt
		  				})
		resp = slacker.api_call("chat.postMessage",
	  					 channel=bot_user,
	  					 as_user=True,
	  					 thread_ts=thread_ts,	  					 
	  					 text="pong",
	  					 attachments=attach)				

		return ""
	else:
		return "got it"

@app.route("/",methods=['GET'])
def hello():			
	return "Hi there! :)"

load_tokens()
if len(api_tokens) == 0: raise RuntimeError
sys.stderr.write(repr(api_tokens))

if __name__ == "__main__": 
	app.run()
