import os
import pytest
import sqlite_backend as backend
import sqlite3
import json

DB_path="DATA/test.db"

try:
	os.remove(DB_path)
except OSError:
	pass

def test_get():
	#create DB
	backend.init(DB_path)
	assert os.path.isfile(DB_path)
	#insert a few rows into the users table
	backend.__put(DB_path, "users", {"id":"1"})
	backend.__put(DB_path, "users", {"id":"2"})
	backend.__put(DB_path, "users", {"id":"3"})
	#make sure rows were inserted
	sql = '''SELECT * FROM users '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql)
	resp =  cursor.fetchall()	
	assert resp[0] == (u'1', 1) 
	assert resp[1] == (u'2', 1) 
	assert resp[2] == (u'3', 1)
	#check if __get returns the same data (no params)
	resp_2 = backend.__get(DB_path, sql, None)
	assert resp == resp_2
	#check if __get returns the same data (with params)
	sql = ''' SELECT * FROM users WHERE id=? '''
	resp_3 = backend.__get(DB_path, sql, ["1"])
	assert resp_3[0] == resp[0]
	os.remove(DB_path)

def test_table_exists():	
	assert not backend.__table_exists(DB_path, "users")	
	USERS = ''' CREATE TABLE users(id TEXT PRIMARY KEY, username TEXT, active INTEGER DEFAULT 1) '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()		
	cursor.execute(USERS)		
	db.commit()	
	db.close()
	assert backend.__table_exists(DB_path, "users")

def test_add_user():
	#create DB
	backend.init(DB_path)
	#create user with default check times
	user_id_1="123"
	#make sure user does not exist	
	assert backend.get_user(DB_path, user_id_1) is None
	#create user
	backend.add_user(DB_path, user_id_1)
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE id=? '''
	cursor.execute(sql, (user_id_1,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == user_id_1 and \
		   resp[backend.USER_ACTIVE] == 1	
	#remove test DB
	os.remove(DB_path)

def test_create_table():
	#create DB
	backend.init(DB_path)	
	fields = ["some_field", "another_field","yet_another_field", "final_field"]
	assert not backend.__table_exists(DB_path, "some_table")
	#create table
	backend.__create_table(DB_path, "some_table", fields)
	#check if table exists	
	assert backend.__table_exists(DB_path, "some_table")	
	#try to create table with the same name *without* ovrride	
	with pytest.raises(sqlite3.OperationalError):
		backend.__create_table(DB_path, "some_table", fields, override=False)	
	#try to create table with the same name *with* ovrride		
	backend.__create_table(DB_path, "some_table", fields, override=True)	
	#check if table exists
	assert backend.__table_exists(DB_path, "some_table")	
	#remove test DB
	os.remove(DB_path)

def test_create_survey():

	backend.init(DB_path)
	sleep_survey = { "survey_id": "sleep",
	 				  "survey": [  { "id": "sleep_hours",
	       							  "question": "how many hours have you slept yesterday?",
		       						   "choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
		    						{ "id": "sleep_quality",
		       						   "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
		       							"choices": [1,2,3,4,5] }  
		       					]
					}
	 

	stress_survey = { "survey_id": "stress",
	 				  "survey": [  {"id": "stress_level",
		       						"question": "In a scale from 1 to 5, how do you rate your stress level ?",
		       						"choices": [1,2,3,4,5] }
	                  			]
					}
	#check that survey tables do not exist
	assert not backend.__table_exists(DB_path, "survey_"+sleep_survey["survey_id"])
	assert not backend.__table_exists(DB_path, "survey_"+stress_survey["survey_id"])
	#create survey
	backend.create_survey(DB_path, sleep_survey)
	backend.create_survey(DB_path, stress_survey)
	#check that survey tables were created
	assert backend.__table_exists(DB_path, "survey_"+sleep_survey["survey_id"])
	assert backend.__table_exists(DB_path, "survey_"+stress_survey["survey_id"])
	#check that the surveys were added to the surveys table
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM surveys WHERE id=? '''
	cursor.execute(sql, (sleep_survey["survey_id"],))
	resp_sleep = cursor.fetchone()		
	assert json.loads(resp_sleep[1]) == sleep_survey
	cursor.execute(sql, (stress_survey["survey_id"],))
	resp_stress = cursor.fetchone()		
	assert json.loads(resp_stress[1]) == stress_survey
	#try to create a survey that already exists
	with pytest.raises(RuntimeError):
		backend.create_survey(DB_path, sleep_survey)
	with pytest.raises(RuntimeError):
		backend.create_survey(DB_path, stress_survey)
	#remove test DB
	os.remove(DB_path)

def test_delete_answers():
	backend.init(DB_path)
	sleep_survey = { "survey_id": "sleep",
	 				  "survey": [  { "id": "sleep_hours",
	       							  "question": "how many hours have you slept yesterday?",
		       						   "choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
		    						{ "id": "sleep_quality",
		       						   "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
		       							"choices": [1,2,3,4,5] }  
		       					]
					}
	#create survey
	backend.create_survey(DB_path, sleep_survey)		
	user_id = "u1"
	survey_id="sleep"	
	#create answers
	#DB_path, user_id, survey_id, ts, response
	
	backend.save_response(DB_path, user_id, survey_id, 200, {"sleep_hours":9,"sleep_quality":5})
	backend.save_response(DB_path, user_id, survey_id, 300, {"sleep_hours":8,"sleep_quality":4})
	backend.save_response(DB_path, user_id, survey_id, 400, {"sleep_hours":7,"sleep_quality":3})	
	
	#check answers ok
	report = backend.get_report(DB_path, user_id, survey_id)	
	print "rep", report
	assert report[0] == (3, user_id, u'400','7','3')
	assert report[1] == (2, user_id, u'300','8','4')
	assert report[2] == (1, user_id, u'200','9','5')	
	backend.delete_answers(DB_path, user_id, survey_id)
	report = backend.get_report(DB_path, user_id, survey_id)	
	assert report == []
	#remove test DB
	os.remove(DB_path)

def test_delete_survey():	
	backend.init(DB_path)	
	#create a survey
	survey_id="stress"
	survey = { "survey_id": survey_id,
			   "survey": [ {"id": "stress_level",
		        			"question": "In a scale from 1 to 5, how do you rate your stress level ?",
		       				"choices": [1,2,3,4,5] } ]
			}		
	# check survey does not exist 
	x = backend.get_survey(DB_path, survey_id)
	assert x == None
	# create survey
	backend.create_survey(DB_path, survey)
	# check survey was created
	x = backend.get_survey(DB_path, survey_id)
	assert x == survey
	# delete_survey(survey_id)
	backend.delete_survey(DB_path, survey["survey_id"])
	# check survey does not exist anymore
	x = backend.get_survey(DB_path, survey_id)
	assert x == None
	os.remove(DB_path)	

def test_get_survey():
	backend.init(DB_path)
	sleep_survey = { "survey_id": "sleep_2",
	 				  "survey": [  { "id": "sleep_hours",
	       							  "question": "how many hours have you slept yesterday?",
		       						   "choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
		    						{ "id": "sleep_quality",
		       						   "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
		       							"choices": [1,2,3,4,5] }  
		       					]
					}	 

	stress_survey = { "survey_id": "stress_2",
	 				  "survey": [  {"id": "stress_level",
		       						"question": "In a scale from 1 to 5, how do you rate your stress level ?",
		       						"choices": [1,2,3,4,5] }
	                  			]
					}	
	#create survey
	backend.create_survey(DB_path, sleep_survey)
	backend.create_survey(DB_path, stress_survey)	
	#check that the surveys were added to the surveys table
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM surveys WHERE id=? '''
	cursor.execute(sql, (sleep_survey["survey_id"],))
	resp_sleep = cursor.fetchone()		
	assert json.loads(resp_sleep[1]) == sleep_survey
	#check that get_survey returns the same
	resp_sleep_get = backend.get_survey(DB_path, sleep_survey["survey_id"])
	assert resp_sleep_get == sleep_survey, resp_sleep_get
	cursor.execute(sql, (stress_survey["survey_id"],))
	resp_stress = cursor.fetchone()		
	assert json.loads(resp_stress[1]) == stress_survey
	resp_stress_get = backend.get_survey(DB_path, stress_survey["survey_id"])
	assert resp_stress_get == stress_survey
	#remove test DB
	os.remove(DB_path)

def test_get_user():
	#create DB
	backend.init(DB_path)	
	user_id="123"
	backend.add_user(DB_path, user_id)			
	#check that user was correctly created
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE id=? '''
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID] == user_id and \
	       resp[backend.USER_ACTIVE] == 1
	#load user
	user = backend.get_user(DB_path, user_id)
	assert user[backend.USER_ID] == user_id and \
	       resp[backend.USER_ACTIVE] == 1
	#remove test DB
	os.remove(DB_path)

def test_insert_row():
	#create the same DB *with* override
	backend.init(DB_path)	
	backend.__put(DB_path, "users", {"id":"silvio"})
	backend.__put(DB_path, "user_surveys", {"user_id":"silvio","survey_id":"some_survey","am_check":"am", "pm_check":"pm"})
	backend.__put(DB_path, "surveys", {"id":"some_survey","survey":"the actual survey"})	
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	

	sql_users = '''SELECT * FROM users '''	
	cursor.execute(sql_users)
	resp_user =  cursor.fetchone()
	assert resp_user == (u'silvio',1) 

	sql_surveys = '''SELECT * FROM surveys '''
	cursor.execute(sql_surveys)
	resp_survey =  cursor.fetchone()	
	assert resp_survey == (u'some_survey', u'the actual survey')

	sql_user_surveys = '''SELECT * FROM user_surveys '''
	cursor.execute(sql_user_surveys)
	resp_user_survey =  cursor.fetchone()	
	assert resp_user_survey == (u'silvio', u'some_survey', u'am',u'pm') 
	
	os.remove(DB_path)		

def test_join_survey():	
	backend.init(DB_path)
	#create user
	user_id = "u1"	
	backend.add_user(DB_path, user_id)
	#create survey
	survey = { "survey_id": "sleep",
			   "survey": [  { "id": "sleep_hours",
							  "question": "how many hours have you slept yesterday?",
   						   "choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
						{ "id": "sleep_quality",
   						   "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
   							"choices": [1,2,3,4,5] }  
   						]
			 }
	
	backend.create_survey(DB_path, survey)	
	#check that user has not joined survey
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	sql = ''' SELECT * FROM user_surveys WHERE user_id=? AND survey_id=? '''	
	cursor.execute(sql,(user_id, survey["survey_id"]))
	resp =  cursor.fetchone()	
	assert resp is None
	#user joins survey	
	backend.join_survey(DB_path, user_id, survey["survey_id"])
	#check user joined survey
	cursor.execute(sql,(user_id, survey["survey_id"]))
	resp =  cursor.fetchone()	
	assert resp[0] == user_id and \
		   resp[1] == survey["survey_id"] and \
		   resp[2] == None and \
		   resp[3] == None 

	#user joins survey that does not exist
	with pytest.raises(RuntimeError):
		backend.join_survey(DB_path, user_id, "random_survey")

	#user joins a survey that was already joined
	with pytest.raises(RuntimeError):
		backend.join_survey(DB_path, user_id, survey["survey_id"])

	os.remove(DB_path)		

def test_list_surveys():
	backend.init(DB_path)
	sleep_survey = { "survey_id": "sleep",
	 				  "survey": [  { "id": "sleep_hours",
	       							  "question": "how many hours have you slept yesterday?",
		       						   "choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
		    						{ "id": "sleep_quality",
		       						   "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
		       							"choices": [1,2,3,4,5] }  
		       					]
					}
	 

	stress_survey = { "survey_id": "stress",
	 				  "survey": [  {"id": "stress_level",
		       						"question": "In a scale from 1 to 5, how do you rate your stress level ?",
		       						"choices": [1,2,3,4,5] }
	                  			]
					}	
	#create surveys
	backend.create_survey(DB_path, sleep_survey)
	backend.create_survey(DB_path, stress_survey)
	#list surveys
	resp = backend.list_surveys(DB_path)
	assert resp[0][0] == "sleep"
	assert resp[1][0] == "stress"
	#delete surveys
	backend.delete_survey(DB_path, "stress")
	backend.delete_survey(DB_path, "sleep")
	#list surveys again 
	resp = backend.list_surveys(DB_path)
	assert resp == []
	#check that user does not have surveys
	user_id = "u1"	
	resp = backend.list_surveys(DB_path,user_id=user_id)
	assert resp == []
	backend.join_survey(DB_path, user_id, "sleep")
	resp = backend.list_surveys(DB_path,user_id=user_id)
	assert resp[0][1] == "sleep"

def test_save_response():
	backend.init(DB_path)
	sleep_survey = { "survey_id": "sleep",
	 				  "survey": [  { "id": "sleep_hours",
	       							  "question": "how many hours have you slept yesterday?",
		       						   "choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
		    						{ "id": "sleep_quality",
		       						   "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
		       							"choices": [1,2,3,4,5] }  
		       					]
					}
	survey_id = "sleep"
	user_id = "u1"
	backend.create_survey(DB_path, sleep_survey)			
	sql = '''SELECT * FROM survey_sleep WHERE user_id=? and id=?'''	
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()		
	#save
	resp_id = backend.save_response(DB_path, user_id, survey_id, 200, {"sleep_hours":9,"sleep_quality":5})
	cursor.execute(sql,(user_id, resp_id))
	resp =  cursor.fetchall()	
	assert resp[0] == (resp_id, user_id, u'200','9', '5')
	#remove test DB
	os.remove(DB_path)

def test_get_report():
	backend.init(DB_path)
	sleep_survey = { "survey_id": "sleep",
	 				  "survey": [  { "id": "sleep_hours",
	       							  "question": "how many hours have you slept yesterday?",
		       						   "choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
		    						{ "id": "sleep_quality",
		       						   "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
		       							"choices": [1,2,3,4,5] }  
		       					]
					}
	
	backend.create_survey(DB_path, sleep_survey)		
	user_id = "u1"
	survey_id="sleep"		
	resp_id_1 = backend.save_response(DB_path, user_id, survey_id, 200, {"sleep_hours":9,"sleep_quality":5})
	resp_id_2 = backend.save_response(DB_path, user_id, survey_id, 300, {"sleep_hours":8,"sleep_quality":4})
	resp_id_3 = backend.save_response(DB_path, user_id, survey_id, 400, {"sleep_hours":7,"sleep_quality":3})	

	report = backend.get_report(DB_path, "u1", sleep_survey["survey_id"])	
	assert report[0] == (resp_id_3, user_id, u'400','7','3')		
	assert report[1] == (resp_id_2, user_id, u'300','8','4')
	assert report[2] == (resp_id_1, user_id, u'200','9','5')	
	#remove test DB
	os.remove(DB_path)


def test_toggle_user():
	backend.init(DB_path)
	#create user	
	backend.add_user(DB_path, "user_id")	
	#check it's active
	user = backend.get_user(DB_path, "user_id")
	assert user[backend.USER_ACTIVE] == 1
	#disable user
	backend.toggle_user(DB_path, "user_id",active=False)
	#check it's inactive
	user = backend.get_user(DB_path, "user_id")
	assert user[backend.USER_ACTIVE] == 0
	#enable user
	backend.toggle_user(DB_path, "user_id",active=True)
	#check it's active
	user = backend.get_user(DB_path, "user_id")
	assert user[backend.USER_ACTIVE] == 1
	os.remove(DB_path)


# 	