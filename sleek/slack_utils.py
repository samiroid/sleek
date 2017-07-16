import pprint


def get_team_name(slack_client):
	resp = slack_client.api_call("team.info") 
	if not resp.get("ok"): 			
		print "\033[31m[error: {}]\033[0m".format(resp["error"])
		return None
	else:
		return resp["team"]["name"]

def list_dms(slack_client):
	resp = slack_client.api_call("im.list")		
	if not resp.get("ok"): 						
		print "\033[31m[error: {}]\033[0m".format(resp["error"])
		return []
	else:
		 dm_ids = {r["id"]:r["user"] for r in resp["ims"] if not r["is_user_deleted"]}
		 return dm_ids

def list_slackers(slack_client):
	resp = slack_client.api_call("users.list")
	users = {}
	if resp.get('ok'):
		# retrieve all users
		members = resp.get('members')
		for user in members:
			if user["deleted"]: continue
			#ignore slackbot
			if 'name' not in user or user.get('id') == "USLACKBOT": continue				
			users[user.get('name')] = user.get('id')							
	else:
		raise RuntimeError("Could not retrieve members list\n{}".format(resp))
	print "*slackers*"
	pprint.pprint(users)
	return users

def open_dm(slack_client, user):
	resp = slack_client.api_call("im.open", user=user)
	if not resp.get("ok"): 			
		print "\033[31m[error: {}]\033[0m".format(resp["error"])
		return None
	else:
		return resp["channel"]["id"]

def post_slack(slack_client, channel, message, ts=None, attach=None):		
		print u"[posting:\"{}\" to channel {}]".format(message,channel)		
		if ts is not None:
			resp = slack_client.api_call("chat.postMessage",
	  					 channel=channel,
	  					 as_user=True,
	  					 thread_ts=ts,
	  					 text=message,
	  					 attachments=attach)
		else:
			resp = slack_client.api_call("chat.postMessage",
	  					 channel=channel,
	  					 as_user=True,	  					 
	  					 text=message,
	  					 attachments=attach)
		
		if not resp.get("ok"): print u"\033[31m[error: {}]\033[0m".format(resp["error"])


