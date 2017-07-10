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
    parser.add_argument('-greet', type=str, default=None, help="channel to send a greeting after connection")
    parser.add_argument('-dbg', action="store_true", help="Debug Mode; Unhandled exceptions explode")
    parser.add_argument('-verbose', action="store_true", help="Verbose Mode")    

    return parser

if __name__ == "__main__":	
	parser = get_parser()
	args = parser.parse_args()	
	confs = json.load(open(args.cfg, 'r'))	 	

	if args.init: localdb = sleek.LocalBackend(confs, create=True)
	else:         localdb = sleek.LocalBackend(confs)		

	if args.surveys is not None:
		sleek.load_surveys(localdb, args.surveys)
	elif args.connect is not None:
		print "[launching Sleek4Slack]"
		api_token = os.getenv(confs["api_token"])
		bot_name  = confs["bot_name"]
		chat_bot = sleek.Sleek4Slack(db=localdb)
		chat_bot.connect(api_token, bot_name, greet_channel=args.greet, verbose=args.verbose, dbg=args.dbg)		
	else:
		raise NotImplementedError("Nothing to do. You can either load surveys or connect to a Slack")
