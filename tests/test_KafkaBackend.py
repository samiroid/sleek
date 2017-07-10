from ipdb import set_trace
import json
import pytest
import sys
import sqlite3
sys.path.append("sleek")
from sleek.backend import KafkaBackend as Backend
from kafka import KafkaConsumer

DB_path="DATA/test.db"

cfg = {
		"local_DB":DB_path,
		"kafka_servers":"localhost",
		"kafka_topic":"dummy",
		"teamId":"team"
		}

user_id="SILVIO"

sleep_survey = { "id": "sleep",
	 				  "questions": [  { "q_id": "sleep_hours",
	       							  	"question": "how many hours have you slept yesterday?",
		       						   	"choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
		    						{ "q_id": "sleep_quality",
		       						  "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
		       						  "choices": [1,2,3,4,5] }  
		       					]
					}
	 
stress_survey = { "id": "stress",
 				  "questions": [  {"q_id": "stress_level",
	       							"question": "In a scale from 1 to 5, how do you rate your stress level ?",
	       							"choices": [1,2,3,4,5] } ]
				}

def __table_exists(table_name):
		"""
			Auxiliary method to check if a table exists
		"""	
		sql = ''' SELECT count(*) FROM sqlite_master WHERE type='table' AND name=? '''
		db = sqlite3.connect(DB_path)
		cursor = db.cursor()		
		cursor.execute(sql, (table_name,))
		resp = cursor.fetchone()[0]			
		return resp == 1

#################################################################
# USER METHODS
#################################################################
def test_add_user():
	#create DB	
	my_backend = Backend(cfg, create=True)
	#make sure user does not exist	
	assert my_backend.get_users(user_id=user_id) == []
	#create user
	assert my_backend.add_user(user_id)
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE id=? '''
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp[Backend.USER_ID]     == user_id and \
		   resp[Backend.USER_ACTIVE] == 1	
	#adding the same user should fail
	assert not my_backend.add_user(user_id)

def test_get_user():
	#create DB
	my_backend = Backend(cfg, create=True)	
	my_backend.add_user(user_id)			
	#check that user was correctly created
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE id=? '''
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp[Backend.USER_ID] == user_id and \
	       resp[Backend.USER_ACTIVE] == 1
	#load user
	user = my_backend.get_users(user_id=user_id)[0]
	assert user[Backend.USER_ID] == user_id and \
	       resp[Backend.USER_ACTIVE] == 1
		
def test_toggle_user():
	my_backend = Backend(cfg, create=True)
	#create user	
	my_backend.add_user(user_id)	
	#check it's active
	user = my_backend.get_users(user_id=user_id)[0]
	assert user[Backend.USER_ACTIVE] == 1
	#disable user
	my_backend.toggle_user(user_id,active=False)
	#check it's inactive
	user = my_backend.get_users(user_id=user_id)[0]
	assert user[Backend.USER_ACTIVE] == 0
	#enable user
	my_backend.toggle_user(user_id, active=True)
	#check it's active
	user = my_backend.get_users(user_id=user_id)[0]
	assert user[Backend.USER_ACTIVE] == 1
	
#################################################################
# SURVEY METHODS
#################################################################

def test_create_survey():
	my_backend = Backend(cfg, create=True)
	
	#check that survey tables do not exist
	assert not __table_exists("survey_"+sleep_survey["id"])
	assert not __table_exists("survey_"+stress_survey["id"])
	#create survey
	my_backend.create_survey(sleep_survey)
	my_backend.create_survey(stress_survey)
	#check that survey tables were created
	assert __table_exists("survey_"+sleep_survey["id"])
	assert __table_exists("survey_"+stress_survey["id"])
	#check that the surveys were added to the surveys table
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM surveys WHERE id=? '''
	cursor.execute(sql, (sleep_survey["id"],))
	resp_sleep = cursor.fetchone()		
	assert json.loads(resp_sleep[1]) == sleep_survey
	cursor.execute(sql, (stress_survey["id"],))
	resp_stress = cursor.fetchone()		
	assert json.loads(resp_stress[1]) == stress_survey
	#try to create a survey that already exists
	with pytest.raises(RuntimeError):
		my_backend.create_survey(sleep_survey)
	with pytest.raises(RuntimeError):
		my_backend.create_survey(stress_survey)	

def test_delete_answers():
	my_backend = Backend(cfg, create=True)	
	#create sleep survey
	my_backend.create_survey(sleep_survey)				
	#save a few answers
	my_backend.save_answer(user_id, sleep_survey["id"], {"sleep_hours":9,"sleep_quality":5, "ts":200})
	my_backend.save_answer(user_id, sleep_survey["id"], {"sleep_hours":8,"sleep_quality":4, "ts":300})
	my_backend.save_answer(user_id, sleep_survey["id"], {"sleep_hours":7,"sleep_quality":3, "ts":400})		
	#check answers ok
	report = my_backend.get_report(user_id, sleep_survey["id"])	
	print "rep", report
	assert report[0] == (3, user_id, u'400','7','3', None)
	assert report[1] == (2, user_id, u'300','8','4', None)
	assert report[2] == (1, user_id, u'200','9','5', None)	
	#delete answers
	my_backend.delete_answers(user_id, sleep_survey["id"])
	#check no answers
	report = my_backend.get_report(user_id, sleep_survey["id"])	
	assert report == []	

def test_get_survey():
	my_backend = Backend(cfg, create=True)	
	#create survey
	my_backend.create_survey(sleep_survey)
	my_backend.create_survey(stress_survey)	
	#check that the surveys were added to the surveys table
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM surveys WHERE id=? '''
	#sleep survey
	cursor.execute(sql, (sleep_survey["id"],))
	resp_sleep = cursor.fetchone()			
	assert json.loads(resp_sleep[1]) == sleep_survey	
	#check that get_survey returns the same
	resp_sleep_get = my_backend.get_survey(sleep_survey["id"])
	assert resp_sleep_get == sleep_survey, resp_sleep_get
	#stress survey
	cursor.execute(sql, (stress_survey["id"],))	
	resp_stress = cursor.fetchone()		
	assert json.loads(resp_stress[1]) == stress_survey
	#check that get_survey returns the same
	resp_stress_get = my_backend.get_survey(stress_survey["id"])
	assert resp_stress_get == stress_survey
	
def test_join_survey():	
	my_backend = Backend(cfg, create=True)		
	my_backend.create_survey(sleep_survey)	
	#check that user has not joined survey
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	sql = ''' SELECT * FROM user_surveys WHERE user_id=? AND survey_id=? '''	
	cursor.execute(sql,(user_id, sleep_survey["id"]))
	resp =  cursor.fetchone()	
	assert resp is None
	#user joins survey	
	my_backend.join_survey(user_id, sleep_survey["id"])
	#check user joined survey
	cursor.execute(sql,(user_id, sleep_survey["id"]))
	resp =  cursor.fetchone()	
	assert resp[0] == user_id and \
		   resp[1] == sleep_survey["id"] and \
		   resp[2] == None and \
		   resp[3] == None 

	#user joins survey that does not exist
	with pytest.raises(RuntimeError):
		my_backend.join_survey(user_id, "random_survey")

	#user joins a survey that was already joined
	with pytest.raises(RuntimeError):
		my_backend.join_survey(user_id, sleep_survey["id"])
		
def test_list_surveys():
	my_backend = Backend(cfg, create=True)	
	#create surveys
	my_backend.create_survey(sleep_survey)
	my_backend.create_survey(stress_survey)
	#list surveys
	resp = my_backend.list_surveys()
	assert resp[0][0] == "sleep"
	assert resp[1][0] == "stress"
	resp = my_backend.list_surveys(user_id=user_id)
	assert resp == []
	my_backend.join_survey(user_id, "sleep")
	resp = my_backend.list_surveys(user_id=user_id)
	assert resp[0][1] == "sleep"

def test_save_answer():
	my_backend = Backend(cfg, create=True)	
	my_backend.create_survey(sleep_survey)			
	sql = '''SELECT * FROM survey_sleep WHERE user_id=? and id=?'''	
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()		
	#save
	resp_id = my_backend.save_answer(user_id, sleep_survey["id"],{"sleep_hours":9,"sleep_quality":5, "ts": 200})
	cursor.execute(sql,(user_id, resp_id))
	resp =  cursor.fetchall()	
	assert resp[0] == (resp_id, user_id, u'200','9', '5', None)
	
def test_kafka_post():
	my_backend = Backend(cfg, create=True)	
	my_backend.create_survey(sleep_survey)				
	consumer = KafkaConsumer(cfg["kafka_topic"], bootstrap_servers=cfg["kafka_servers"].split(), auto_offset_reset='earliest')
	#save answer
	ans = {"sleep_hours":9,"sleep_quality":5, "ts": 200}
	my_backend.save_answer(user_id, sleep_survey["id"], ans)	
	r = json.loads(consumer.next().value)["responses"]	
	assert r == ans

#################################################################
# REMINDER METHODS
#################################################################

def test_reminders():
	my_backend = Backend(cfg, create=True)	
	my_backend.create_survey(sleep_survey)		
	#user joins survey	
	my_backend.join_survey(user_id, sleep_survey["id"])
	rems = my_backend.get_reminders()
	assert rems[0] == (u'SILVIO', u'sleep', None, None)
	#add AM reminder
	my_backend.set_reminder(user_id, sleep_survey["id"], "10:00AM")
	rems = my_backend.get_reminders()
	assert rems[0] == (u'SILVIO', u'sleep', "10:00AM", None)
	#new AM reminder
	my_backend.set_reminder(user_id, sleep_survey["id"], "9:00AM")
	rems = my_backend.get_reminders()
	assert rems[0] == (u'SILVIO', u'sleep', "9:00AM", None)
	#add PM reminder
	my_backend.set_reminder(user_id, sleep_survey["id"], "2:00PM")
	rems = my_backend.get_reminders()
	assert rems[0] == (u'SILVIO', u'sleep', "9:00AM", "2:00PM")
	#remove reminders
	my_backend.set_reminder(user_id, sleep_survey["id"], None)
	rems = my_backend.get_reminders()
	assert rems[0] == (u'SILVIO', u'sleep', None, None)

#################################################################
# REPORT METHODS
#################################################################	
def test_get_report():
	my_backend = Backend(cfg, create=True)	
	#create sleep survey
	my_backend.create_survey(sleep_survey)				
	#save a few answers
	my_backend.save_answer(user_id, sleep_survey["id"], {"sleep_hours":9,"sleep_quality":5, "ts":200,"notes":"this a nifty note"})
	my_backend.save_answer(user_id, sleep_survey["id"], {"sleep_hours":8,"sleep_quality":4, "ts":300,"notes":"this a another note"})
	my_backend.save_answer(user_id, sleep_survey["id"], {"sleep_hours":7,"sleep_quality":3, "ts":400,"notes":"this a neatfull note"})		
	#check answers ok
	report = my_backend.get_report(user_id, sleep_survey["id"])	
	print "rep", report
	assert report[0] == (3, user_id, u'400','7','3', "this a neatfull note")
	assert report[1] == (2, user_id, u'300','8','4', "this a another note")
	assert report[2] == (1, user_id, u'200','9','5', "this a nifty note")	

def test_get_notes():
	my_backend = Backend(cfg, create=True)	
	#create sleep survey
	my_backend.create_survey(sleep_survey)				
	#save a few answers
	my_backend.save_answer(user_id, sleep_survey["id"], {"sleep_hours":9,"sleep_quality":5, "ts":200,"notes":"this a nifty note"})
	my_backend.save_answer(user_id, sleep_survey["id"], {"sleep_hours":8,"sleep_quality":4, "ts":300,"notes":"this a another note"})
	my_backend.save_answer(user_id, sleep_survey["id"], {"sleep_hours":7,"sleep_quality":3, "ts":400,"notes":"this a neatfull note"})		
	#check answers ok
	report = my_backend.get_notes(user_id, sleep_survey["id"])	
	print "rep", report
	assert report[0] == ( u'400', "this a neatfull note")
	assert report[1] == ( u'300', "this a another note")
	assert report[2] == ( u'200', "this a nifty note")	

