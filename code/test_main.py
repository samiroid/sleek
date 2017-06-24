import pytest
import sqlite_backend as backend
import main
import os

DB_path="DATA/test.db"

try:
	os.remove(DB_path)
except OSError:
	pass

def test_load_surveys():
	"""
		Loads surveys in batch mode
		path: path to folder containing surveys in json format
	"""
	surveys_path="DATA/surveys/"
	backend.init(DB_path)	
	assert backend.get_survey(DB_path, "sleep") == []
	assert backend.get_survey(DB_path, "stress") == []
	main.load_surveys(DB_path, surveys_path)	
	assert backend.get_survey(DB_path, "sleep") != []
	assert backend.get_survey(DB_path, "stress") != []
	os.remove(DB_path)
	

# def test_run_server():
# 	backend.init(DB_path)	

# 	os.remove(DB_path)
# 	assert True == False

# def test_run_local():
# 	backend.init(DB_path)	

# 	os.remove(DB_path)
# 	assert True == False

# def test_sync_users():
# 	backend.init(DB_path)	

# 	os.remove(DB_path)
# 	assert True == False

if __name__ == "__main__":
	backend.init(DB_path,override=False)
	