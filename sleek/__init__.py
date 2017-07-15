from _sleek import Sleek
from slack import Sleek4Slack
from backend import LocalBackend, KafkaBackend
import os
import json

def load_surveys(backend, survey_path):
	"""
		Loads surveys in batch mode
		survey_path: path to folder containing surveys in json format
	"""
	print "[loading surveys @ {}]".format(survey_path)
	ignored = []
	for fname in os.listdir(survey_path):	
		path = survey_path+fname
		if os.path.splitext(path)[1]!=".json":
			ignored.append(fname)			
			continue	
		try:		
			with open(path, 'r') as f:					
				try:
					survey = json.load(f)				
				except ValueError:
					print "invalid json @{}".format(fname)
					continue
				try:
					backend.create_survey(survey)			
				except RuntimeError as e:
					print e

		except IOError:
			ignored.append(path)	
	if len(ignored) > 0:
		print "[ignored the files: {}]".format(repr(ignored))
