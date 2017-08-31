import argparse
import json
import os
import sys
sys.path.insert(0,'..')
from sleek import Backend, Sleek4Slack
from ipdb import set_trace

def get_parser():
    parser = argparse.ArgumentParser(description="Sleek@Slack")
    parser.add_argument('-cfg', type=str, required=True, 
    					help="path a config file (json)")
    parser.add_argument('-init', action="store_true", 
    					help="Initializes the backend")
    parser.add_argument('-surveys', type=str, 
    					help='path to a folder with the surveys in json format')    
    parser.add_argument('-api_token_id', type=str, 
    					help="API token ID to connect to Slack")        
    parser.add_argument('-api_token_from', type=str, default="env", 
    					help="method to retrieve the API token")        
    parser.add_argument('-dbg', action="store_true", 
    					help="Debug Mode (unhandled exceptions explode)")
    parser.add_argument('-verbose', action="store_true", help="Verbose Mode")
    parser.add_argument('-connect', action="store_true", 
    					 help="Connect to a Slack")   
    parser.add_argument('-greet_at', type=str, default=None, 
    					 help="Slack channel to greet users uppon connection")   

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
	if args.init:
		db = Backend(confs,init=True)	
		print "[backend @ {} was initialized]".format(confs["local_DB"])
	if args.surveys is not None:		
		db = Backend(confs)
		db.load_surveys(args.surveys)
		print "loaded surveys"
	elif args.connect:
		sleek4slack = Sleek4Slack(confs, fancy_msgs=True)
		api_token = get_api_token(args.api_token_id,
								  args.api_token_from)		
		sleek4slack.connect(api_token)						
		if args.greet_at is not None:
			sleek4slack.greet_channel(args.greet_at)		
		sleek4slack.listen(verbose=args.verbose, dbg=args.dbg)			
	else:
		raise NotImplementedError("Nothing to do. You can either load surveys or connect to a Slack")
