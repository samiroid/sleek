import argparse
from backend import Backend
import json
from slackclient import SlackClient
import sleek_4_slack as sleek
import os
try:
	from ipdb import set_trace
except ImportError:
	from pdb import set_trace

def load_surveys(backend, survey_path):
	"""
		Loads surveys in batch mode
		survey_path: path to folder containing surveys in json format
	"""
	ignored = []
	for fname in os.listdir(survey_path):	
		path = survey_path+fname
		if os.path.splitext(path)[1]!=".json":
			ignored.append(fname)			
			continue	
		try:		
			with open(path, 'r') as f:					
				survey = json.load(f)				
				backend.create_survey(survey)			
		except IOError:
			ignored.append(path)	
	if len(ignored) > 0:
		print "[ignored the files: {}]".format(repr(ignored))

def get_parser():
    parser = argparse.ArgumentParser(description="Development Sleek")
    parser.add_argument('-cfg', type=str, required=True, help="path a config file (json)")
    parser.add_argument('-init', action="store_true", help="Initializes the backend")
    parser.add_argument('-load_surveys', type=str, help='path to a folder with the surveys in json format')     
    parser.add_argument('-connect', type=str, nargs=2, help="connect [TOKEN_API] [BOT_USERNAME]")        
    parser.add_argument('-greet', type=str, default=None, help="channel to send a greeting after connection")
    parser.add_argument('-dbg', action="store_true", help="Debug Mode; Unhandled exceptions explode")
    parser.add_argument('-verbose', action="store_true", help="Verbose Mode")    

    return parser

if __name__ == "__main__":	
	parser = get_parser()
	args = parser.parse_args()	
	confs = json.load(open(args.cfg, 'r'))	 	
	if args.init:
		print "[initializing backend]"		
		local_backend = Backend(confs, create=True)
	else:
		local_backend = Backend(confs)		

	if args.load_surveys is not None:
		print "[loading surveys @ {}]".format(args.load_surveys)
		load_surveys(local_backend, args.load_surveys)
	elif args.connect is not None:
		print "[launching Sleek4Slack]"
		api_token = args.connect[0]
		bot_name  = args.connect[1]
		sleek_client = sleek.Sleek4Slack(db=local_backend)
		sleek_client.connect(api_token, bot_name, greet_channel=args.greet, verbose=args.verbose, dbg=args.dbg)		
	else:
		raise NotImplementedError("Nothing to do. You can either load surveys or connect to a Slack")
