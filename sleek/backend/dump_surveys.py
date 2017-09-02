import argparse
from local_backend import Backend

def get_parser():
    parser = argparse.ArgumentParser(description="Dump User Surveys")
    parser.add_argument('-db', type=str, required=True, 
    					help="path to the DB")    
    parser.add_argument('-output', type=str, 
    					help='path to the output folder')    
    return parser

if __name__ == "__main__":	
	parser = get_parser()
	args = parser.parse_args()		
	confs = {"local_DB":args.db}	
	db = Backend(confs)	
	db.dump_surveys(args.output)	
