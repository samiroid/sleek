import argparse
import json
import sleek
import sqlite_backend as backend
import os

def delete_survey(DB_path, survey_id):
	"""
		Delete a survey
		survey_id: survey id
	"""
	backend.delete_survey(DB_path, survey_id)

def load_surveys(DB_path, path):
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
			backend.create_survey(DB_path, survey)			

def run_server():
	raise NotImplementedError

def run_local():
	raise NotImplementedError

def sync_users():
	raise NotImplementedError

def upload_survey(DB_path, survey):
	"""
		Uploads a survey
		survey: a dictionary specifying a survey
	"""
	backend.create_survey(DB_path, survey)

def get_parser():
    parser = argparse.ArgumentParser(description="Main Sleek")
    parser.add_argument('-load_surveys', type=str, help='path to a folder with the surveys in json format')     
    parser.add_argument('-api_token', type=str, help="Slack API token")
    parser.add_argument('-server_mode', type=bool, action="store_true")
    


    # parser.add_argument('-output', type=str, required=True,
    #                     help='output folder')       
    # parser.add_argument('-feats', type=str, choices=['bow_bin','boe_bin','boe_freq'], nargs='+',
    #                     help='features')                             
    # parser.add_argument('-cue_feats', type=str, nargs=2,
    #                     help='features')        
    # parser.add_argument('-w2v', type=str, nargs='+',
    #                     help='path to WORD embeddings')
    # parser.add_argument('-u2v', type=str, nargs='+',
    #                     help='path to USER embeddings')
    # parser.add_argument('-bwc', type=str, 
    #                     help='path to brown clusters')    
    # parser.add_argument('-lda', type=str, nargs=2,
    #                     help='path to LDA and LDA idx')    
    # parser.add_argument('-vocab_size', type=int, 
    #                     help='max number of types to keep in the vocabulary')    
    return parser

if __name__=="__main__":	
	parser = get_parser()
	args = parser.parse_args()


