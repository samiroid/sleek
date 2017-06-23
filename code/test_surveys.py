import os
import pytest
import sqlite_backend as backend
import sqlite3

DB_path="DATA/test.db"

try:
	os.remove(DB_path)
except OSError:
	pass

def test_add_user():
	#create DB

def test_sleep_survey():
	#create DB
	backend.init(DB_path)
	response = {"sleep_hours":7, "sleep_quality":4} 
	ts = 100
	#check that survey does not exist yet
	resp = backend.get_survey(DB_path, "sleep_survey", "user_id", ts)
	assert resp is None
	backend.save_survey(DB_path, "user_id", "sleep_survey", ts, response)
	resp = backend.get_survey(DB_path, "sleep_survey", "user_id", ts)
	assert resp[0] ==  "user_id" and \
		   resp[1] == ts and \
		   resp[2] == response["sleep_hours"] and \
		   resp[3] == response["sleep_quality"]
	#remove test DB
	os.remove(DB_path)

def test_stress_survey():
	#create DB
	backend.init(DB_path)
	response = {"stress":4} 
	ts = 100
	#check that survey does not exist yet
	resp = backend.get_survey(DB_path, "stress_survey", "user_id", ts)
	assert resp is None
	backend.save_survey(DB_path, "user_id", "stress_survey", ts, response)
	resp = backend.get_survey(DB_path, "stress_survey", "user_id", ts)
	assert resp[0] ==  "user_id" and \
		   resp[1] == ts and \
		   resp[2] == response["stress"]
		   
	#remove test DB
	os.remove(DB_path)

