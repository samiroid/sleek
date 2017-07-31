from flask import Flask, request
from datetime import datetime
import json
import pprint
from slackclient import SlackClient
from pdb import set_trace
import quinn.loqsmith as loqsmith

LOG = "/tmp/foo.log"
api_tokens = {"samiroid":"xoxb-212432954930-DoLkGjeqXBSjYz6ikjHKRJOR",
			  "sleek4":"xoxb-206839775285-0H2SfMdQfHNc5yD7ikDwwoZC"}

api_tokens = {}

def get_api_token(key, method="env"):
	if method == "env":
		return os.getenv(key)
	elif method == "env":
		tok = loqsmith.get_token(key)	
		return tok.oauth_token.access_token
	else:
		raise NotImplementedError

def load_tokens():
	with open("pongconf.txt") as f:
		f.next()
		for l in f:
			team, method, key = l.split()
			api_token[team] = get_api_token(method, key)

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

if __name__ == "__main__": 
	load_tokens()
	print api_token
	app.run()
