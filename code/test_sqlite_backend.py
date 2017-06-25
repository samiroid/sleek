import os
import pytest
import sqlite_backend as backend
import sqlite3

DB_path="DATA/test.db"

try:
	os.remove(DB_path)
except OSError:
	pass

def test_get():
	#create DB
	backend.init(DB_path,override=True)
	assert os.path.isfile(DB_path)
	#insert a few rows into the users table
	backend.__put(DB_path, "users", {"id":"1","username":"user 1"})
	backend.__put(DB_path, "users", {"id":"2","username":"user 2"})
	backend.__put(DB_path, "users", {"id":"3","username":"user 3"})
	#make sure rows were inserted
	sql = '''SELECT * FROM users '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql)
	resp =  cursor.fetchall()	
	assert resp[0] == (u'1', u'user 1',1) 
	assert resp[1] == (u'2', u'user 2',1) 
	assert resp[2] == (u'3', u'user 3',1)
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
	backend.init(DB_path,override=True)
	#create user with default check times
	username_1="alice"
	user_id_1="123"
	#make sure user does not exist	
	user = backend.get_user(DB_path, user_id_1)
	assert user == []
	backend.add_user(DB_path, user_id_1, username_1)
	#create user with specific check times
	username_2="bob"
	user_id_2="456"	
	backend.add_user(DB_path, user_id_2, username_2)	
	#check that username_1 was correctly created
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE id=? '''
	cursor.execute(sql, (user_id_1,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == user_id_1 and \
		   resp[backend.USER_NAME] == username_1
	#check that username_2 was correctly created
	cursor.execute(sql, (user_id_2,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]  == user_id_2 and \
	       resp[backend.USER_NAME] == username_2 and \
	       resp[backend.USER_ACTIVE] == 1
	#remove test DB
	os.remove(DB_path)

def test_create_table():
	#create DB
	backend.init(DB_path, override=True)	
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

	backend.init(DB_path,override=True)
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
	assert resp_sleep[1] == repr(sleep_survey)
	cursor.execute(sql, (stress_survey["survey_id"],))
	resp_stress = cursor.fetchone()		
	assert resp_stress[1] == repr(stress_survey)
	#remove test DB
	os.remove(DB_path)

def test_delete_user():
	#create DB
	backend.init(DB_path,override=True)
	#create user 
	username="alice"
	user_id="123"
	backend.add_user(DB_path, user_id, username)			
	#check that user was correctly created
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE id=? '''
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == user_id and \
		   resp[backend.USER_NAME] == username and \
	       resp[backend.USER_ACTIVE] == 1
	#remove user
	backend.delete_user(DB_path, user_id)
	#check user does not exist
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp is None	
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
	assert x == [], repr(x)
	# create survey
	backend.create_survey(DB_path, survey)
	# check survey was created
	x = backend.get_survey(DB_path, survey_id)
	assert x == repr(survey), repr(x)
	# delete_survey(survey_id)
	backend.delete_survey(DB_path, survey["survey_id"])
	# check survey does not exist anymore
	x = backend.get_survey(DB_path, survey_id)
	assert x == [], repr(x)
	os.remove(DB_path)	

def test_get_survey():
	backend.init(DB_path,override=True)
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
	assert resp_sleep[1] == repr(sleep_survey)
	#check that get_survey returns the same
	resp_sleep_get = backend.get_survey(DB_path, sleep_survey["survey_id"])
	assert resp_sleep_get == repr(sleep_survey), repr(resp_sleep_get)
	cursor.execute(sql, (stress_survey["survey_id"],))
	resp_stress = cursor.fetchone()		
	assert resp_stress[1] == repr(stress_survey)
	resp_stress_get = backend.get_survey(DB_path, stress_survey["survey_id"])
	assert resp_stress_get == repr(stress_survey)
	#remove test DB
	os.remove(DB_path)

def test_get_user():
	#create DB
	backend.init(DB_path,override=True)	
	username="alice"
	user_id="123"
	backend.add_user(DB_path, user_id, username)			
	#check that user was correctly created
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE id=? '''
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == user_id and \
		   resp[backend.USER_NAME] == username and \
	       resp[backend.USER_ACTIVE] == 1
	#load user
	user = backend.get_user(DB_path, user_id)
	assert user[backend.USER_ID]   == user_id and \
		   user[backend.USER_NAME] == username and \
	       resp[backend.USER_ACTIVE] == 1
	#remove test DB
	os.remove(DB_path)

def test_init():	
	#check that DB does not exit
	assert not os.path.isfile(DB_path)
	#create DB
	backend.init(DB_path,override=True)
	assert os.path.isfile(DB_path)
	#insert a few rows into the users table
	backend.__put(DB_path, "users", {"id":"1","username":"user 1"})
	backend.__put(DB_path, "users", {"id":"2","username":"user 2"})
	backend.__put(DB_path, "users", {"id":"3","username":"user 3"})
	#make sure rows are preserved
	sql = '''SELECT * FROM users '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql)
	resp =  cursor.fetchall()	
	assert resp[0] == (u'1', u'user 1',1) 
	assert resp[1] == (u'2', u'user 2',1) 
	assert resp[2] == (u'3', u'user 3',1)
	#create the same DB *without* override	
	backend.init(DB_path,override=False)
	sql = '''SELECT * FROM users '''	
	cursor.execute(sql)
	resp_2 =  cursor.fetchall()	
	assert resp_2[0] == (u'1', u'user 1',1) 
	assert resp_2[1] == (u'2', u'user 2',1) 
	assert resp_2[2] == (u'3', u'user 3',1)
	#create the same DB *with* override
	backend.init(DB_path,override=True)
	#make sure the users table is empty
	cursor.execute(sql)
	resp_3 =  cursor.fetchall()	
	assert resp_3 == []
	os.remove(DB_path)

def test_insert_row():
	#create the same DB *with* override
	backend.init(DB_path,override=True)
	backend.__create_table(DB_path, "some_table", ["a_field","b_field","sea_field"],override=True)
	backend.__put(DB_path, "some_table", {"a_field":"a_field_1","b_field":"b_field_1","sea_field":"sea_field_1"})
	backend.__put(DB_path, "some_table", {"a_field":"a_field_2","b_field":"b_field_2","sea_field":"sea_field_2"})
	backend.__put(DB_path, "some_table", {"a_field":"a_field_3","b_field":"b_field_3","sea_field":"sea_field_3"})
	sql = '''SELECT * FROM some_table '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql)
	resp =  cursor.fetchall()	
	assert resp[0] == (u'a_field_1', u'b_field_1', u'sea_field_1') 
	assert resp[1] == (u'a_field_2', u'b_field_2', u'sea_field_2') 
	assert resp[2] == (u'a_field_3', u'b_field_3', u'sea_field_3')
	os.remove(DB_path)		

def test_join_survey():	
	backend.init(DB_path,override=True)
	#create user
	user_id = "u1"
	username = "user 1"
	backend.add_user(DB_path, user_id, username)
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
	am_check = '10'
	pm_check = '5'
	backend.join_survey(DB_path, user_id, survey["survey_id"], am_check, pm_check )
	#check user joined survey
	cursor.execute(sql,(user_id, survey["survey_id"]))
	resp =  cursor.fetchone()	
	assert resp[0] == user_id and \
		   resp[1] == survey["survey_id"] and \
		   resp[2] == am_check and \
		   resp[3] == pm_check

	#user joins survey that does not exist
	with pytest.raises(RuntimeError):
		backend.join_survey(DB_path, user_id, "random_survey", am_check, pm_check )

	#user joins a survey that was already joined
	with pytest.raises(RuntimeError):
		backend.join_survey(DB_path, user_id, survey["survey_id"], am_check, pm_check )

	os.remove(DB_path)		

# # def test_list_surveys():
# # 	assert True == False

def test_save_response():
	backend.init(DB_path,override=True)
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
	#check that survey tables were created
	assert backend.__table_exists(DB_path, "survey_"+sleep_survey["survey_id"])
	resp_1 = {"user_id":"u1", "timestamp":100,"sleep_hours":4,"sleep_quality":3}
	resp_2 = {"user_id":"u1", "timestamp":200,"sleep_hours":3,"sleep_quality":1}
	backend.save_response(DB_path, sleep_survey["survey_id"], resp_1)
	backend.save_response(DB_path, sleep_survey["survey_id"], resp_2)
	
	sql = '''SELECT * FROM survey_sleep '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql)
	resp =  cursor.fetchall()	
	assert resp[0] == (u'u1', u'100','4','3')
	assert resp[1] == (u'u1', u'200','3','1')
	#remove test DB
	os.remove(DB_path)

def test_get_report():
	backend.init(DB_path,override=True)
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
	#check that survey tables were created
	assert backend.__table_exists(DB_path, "survey_"+sleep_survey["survey_id"])
	resp_1 = {"user_id":"u1", "timestamp":100,"sleep_hours":4,"sleep_quality":3}
	resp_2 = {"user_id":"u1", "timestamp":400,"sleep_hours":3,"sleep_quality":1}
	resp_3 = {"user_id":"u1", "timestamp":300,"sleep_hours":8,"sleep_quality":2}
	resp_4 = {"user_id":"u1", "timestamp":200,"sleep_hours":8,"sleep_quality":4}
	backend.save_response(DB_path, sleep_survey["survey_id"], resp_1)
	backend.save_response(DB_path, sleep_survey["survey_id"], resp_2)
	backend.save_response(DB_path, sleep_survey["survey_id"], resp_3)
	backend.save_response(DB_path, sleep_survey["survey_id"], resp_4)
	
	report = backend.get_report(DB_path, "u1", sleep_survey["survey_id"])	
	assert report[0] == (u'u1', u'400','3','1')
	assert report[1] == (u'u1', u'300','8','2')
	assert report[2] == (u'u1', u'200','8','4')
	assert report[3] == (u'u1', u'100','4','3')	
	
	#remove test DB
	os.remove(DB_path)


def test_toggle_user():
	backend.init(DB_path,override=True)
	#create user	
	backend.add_user(DB_path, "user_id", "username")	
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

def test_toggle_survey():
	backend.init(DB_path,override=True)
	#create user		
	user_id="u1"
	survey_id="some_survey"
	survey = {"user_id":user_id,"survey_id":survey_id,"pm_check":"1","am_check":"2"}
	backend.__put(DB_path, "user_surveys", survey)
	#check it's *active*
	sql = '''SELECT * FROM user_surveys WHERE user_id=? AND survey_id=?'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql,(user_id,survey_id))
	resp =  cursor.fetchone()		
	assert resp[backend.SURVEYS_ACTIVE] == 1
	#disable user survey
	backend.toggle_survey(DB_path, user_id, survey_id, active=False)
	#check it's *inactive*
	cursor.execute(sql,(user_id,survey_id))
	resp =  cursor.fetchone()		
	assert resp[backend.SURVEYS_ACTIVE] == 0
	#enable user survey
	backend.toggle_survey(DB_path, user_id, survey_id, active=True)
	#check it's *active* again
	cursor.execute(sql,(user_id,survey_id))
	resp =  cursor.fetchone()		
	assert resp[backend.SURVEYS_ACTIVE] == 1
# 	