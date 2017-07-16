import argparse
import json
import sleek
import os

try:
	from ipdb import set_trace
except ImportError:
	from pdb import set_trace

def get_parser():
    parser = argparse.ArgumentParser(description="Sleek@Slack")
    parser.add_argument('-cfg', type=str, required=True, help="path a config file (json)")
    parser.add_argument('-init', action="store_true", help="Initializes the backend")
    parser.add_argument('-surveys', type=str, help='path to a folder with the surveys in json format')     
    parser.add_argument('-connect', action="store_true", help="Connect to Slack")        
    parser.add_argument('-dbg', action="store_true", help="Debug Mode; Unhandled exceptions explode")
    parser.add_argument('-verbose', action="store_true", help="Verbose Mode")    

    return parser

def get_api_token(key, method="env"):
	if method == "env":
		return os.getenv(key)
	else:
		raise NotImplementedError

if __name__ == "__main__":	
	parser = get_parser()
	args = parser.parse_args()	
	confs = json.load(open(args.cfg, 'r'))	 		
	
	if confs["backend_type"]=="local":
		db = sleek.LocalBackend(confs, create=args.init)
	elif confs["backend_type"]=="kafka":
		db = sleek.KafkaBackend(confs, create=args.init)		
	else:
		raise NotImplementedError

	if args.surveys is not None:
		sleek.load_surveys(db, args.surveys)
	elif args.connect is not None:				
		chat_bot = sleek.Sleek4Slack(db=db)
		api_token = get_api_token(confs["api_token"],confs["get_token_from"])
		bot_name  = confs["bot_name"]
		greet_channel = confs["greet_channel"]
		if confs["survey_mode"]	== "interactive":
			interactive=True
		elif confs["survey_mode"] == "text":
			interactive=False
		else:
			raise NotImplementedError
		chat_bot.connect(api_token, bot_name)				
		if len(greet_channel) > 0:
			chat_bot.greet_channel(greet_channel)		
		chat_bot.listen(interactive=interactive, verbose=args.verbose, dbg=args.dbg)			
	else:
		raise NotImplementedError("Nothing to do. You can either load surveys or connect to a Slack")
