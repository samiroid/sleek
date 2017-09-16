from datetime import datetime
from flask import Flask, request
import json
import pprint
from pdb import set_trace
from slackclient import SlackClient

app = Flask(__name__) 
@app.route("/sleek",methods=['GET', 'POST'])
def sleek():				
	if request.method == 'POST':			
		payload = json.loads(request.form['payload'])				
		
		bot = payload["original_message"]["user"]
		slack_user, api_token = payload["callback_id"].split("@")		
		thread_ts = payload["original_message"]["ts"]
		action = payload['actions'][0]		
		question = action["name"]
		if action["type"] == "button":			
			ans = action["value"]
		elif action["type"] == "select":
			ans = action["selected_options"][0]["value"]
		reply = question + " " + ans				
		key = payload["team"]["domain"]
		del payload["original_message"]
		pprint.pprint(payload)
		print "key: {}".format(key)		
		slacker = SlackClient(api_token)
		attach = []
		attach.append({ "fallback": "pong",
        		 		"text": reply,
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
		return "ponged :)"

@app.route("/",methods=['GET'])
def hello():			
	return "Hi there! :)"

if __name__ == "__main__": 
	app.run()
