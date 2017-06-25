import argparse
import json
from slack import Sleek4Slack
import os
from ipdb import set_trace


def load_surveys(sleek_instance, path):
	"""
		Loads surveys in batch mode
		path: path to folder containing surveys in json format
	"""
	for fname in os.listdir(path):	
		if os.path.splitext(path+fname)[1]!=".json":
			print "ignored %s"% fname 
			continue			
		with open(path+fname, 'r') as f:					
			survey = json.load(f)
			sleek_instance.create_survey(survey)	

def get_parser():
    parser = argparse.ArgumentParser(description="Main Sleek")
    # parser.add_argument('-load_surveys', type=str, help='path to a folder with the surveys in json format')     
    parser.add_argument('-api_token', type=str, required=True, help="Slack API token")
    parser.add_argument('-backend', type=str, required=True, help="path to the backend DB")

    return parser

if __name__=="__main__":	
	parser = get_parser()
	args = parser.parse_args()
	api_token = args.api_token
	DB_path   = args.backend
	sleek = Sleek4Slack(api_token, DB_path, "dude")
	sleek.connect("#general",dbg=False)
