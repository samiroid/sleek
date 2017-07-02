import argparse
import json
import sleek_4_slack as sleek
from slackclient import SlackClient
import os
from ipdb import set_trace


def load_surveys(sleek_instance, survey_path):
	"""
		Loads surveys in batch mode
		survey_path: path to folder containing surveys in json format
	"""
	ignored = []
	loaded  = []
	for fname in os.listdir(survey_path):	
		path = survey_path+fname
		if os.path.splitext(path)[1]!=".json":
			ignored.append(fname)			
			continue	
		try:		
			with open(path, 'r') as f:					
				survey = json.load(f)				
				sleek_instance.upload_survey(survey)	
				loaded.append(survey["survey_id"])
		except IOError:
			ignored.append(path)
	
	if len(ignored) > 0:
		s =  "[ignored the files: {}]".format(repr(ignored))
		print sleek.colstr(s, "red")	

def get_bot_id(botname,api_token):	
	slack_client = SlackClient(api_token)
	resp = slack_client.api_call("users.list")		
	bot_id = None	
	if resp.get('ok'):
		# retrieve all users
		members = resp.get('members')
		for m in members:			
			print m.get('name'), m.get('id')
			if 'name' in m and m.get('name') == botname:				
				bot_id= m.get('id')				
	else:
		raise RuntimeError("Could not retrieve members list\n{}".format(resp))		
	return bot_id

def get_parser():
    parser = argparse.ArgumentParser(description="Main Sleek")
    parser.add_argument('-load_surveys', type=str, help='path to a folder with the surveys in json format')     
    parser.add_argument('-connect', type=str, nargs=2, help="connect [TOKEN_API] [BOT_USER_ID]")
    parser.add_argument('-bot_id', type=str, help="Sleek User ID @Slack")
    parser.add_argument('-db', type=str, help="path to the backend DB")
    parser.add_argument('-init', action="store_true", help="Initializes the backend")
    parser.add_argument('-dbg', action="store_true", help="Debug Mode; Unhandled exceptions explode")
    parser.add_argument('-verbose', action="store_true", help="Verbose Mode")
    parser.add_argument('-get_bot_id', type=str, nargs=2, help="get bot id [TOKEN_API] [BOT_USER_NAME]")
    parser.add_argument('-api_token', type=str, help="token api")
    

    return parser

if __name__=="__main__":	
	parser = get_parser()
	args = parser.parse_args()	
	DB_path   = args.db	
	surveys_path = args.load_surveys	
	
	if args.get_bot_id is not None:
		api_token, botname = args.get_bot_id 
		print get_bot_id(botname, api_token )
	else:
		if args.init:
			print "[initializing backend]"		
		sleek_client = sleek.Sleek4Slack(DB_path, init_backend=args.init)
		if surveys_path is not None:
			print "[loading surveys @ {}]".format(surveys_path)
			load_surveys(sleek_client, surveys_path)
		if args.connect is not None:
			print "[launching Sleek4Slack]"
			api_token = args.connect[0]
			bot_id    = args.connect[1]
			sleek_client.connect(api_token, greet=True)
			sleek_client.listen(bot_id, dbg=args.dbg, verbose=args.verbose)
