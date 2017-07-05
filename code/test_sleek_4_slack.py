from datetime import datetime
from ipdb import set_trace
import json
import os
import pytest
import sqlite_backend as backend
from sleek import Sleek
from sleek_4_slack import Sleek4Slack
import status
from datetime import datetime

DB_path="DATA/test_slack.db"

bot_name="dude"
api_token = os.environ.get('SLACK_BOT_TOKEN')
some_user="U5TCJ682Z"
context = {"user_id":some_user,"ts":1,"thread_ts":2}

def test_confs():
	print "hello"
	cfg={ 
		  "greet": ["ciao","oi","holla :)"],
		  "announce": "This is a test chat bot",
		  "nack": ["q?!", "no lo se","!?"],
	      "ack": ["roger","okidoki"],
		  "help": "Please some help!"	
		}
	#create Sleek instance with default config
	bot = Sleek()
	assert bot.greet() in Sleek.default_cfg["greet"]
	assert bot.ack() in Sleek.default_cfg["ack"]
	assert bot.nack() in Sleek.default_cfg["nack"]
	assert bot.announce() == Sleek.default_cfg["announce"]
	assert bot.help() == Sleek.default_cfg["help"]

	#create Sleek instance with custom config
	bot2 = Sleek(cfg=cfg)
	assert bot2.greet() in cfg["greet"]
	assert bot2.ack() in cfg["ack"]
	assert bot2.nack() in cfg["nack"]
	assert bot2.help() in cfg["help"]
	assert bot2.announce() in cfg["announce"]

def test_load_surveys():
	sleek = Sleek4Slack(DB_path, init_backend=True)	
	assert len(sleek.current_surveys) == 0
	survey = json.load(open("DATA/surveys/sleep.json", 'r'))				
	assert sleek.upload_survey(survey)
	# sleek.connect(api_token)	
	# set_trace()
	assert backend.get_survey(DB_path, "sleep") is not None
	assert not sleek.upload_survey(survey)
	os.remove(DB_path)

def test_join():
	sleek = Sleek4Slack(DB_path, init_backend=True)		
	# sleek.connect(api_token)		
	survey_id = "sleep"
	survey = json.load(open("DATA/surveys/sleep.json", 'r'))				
	survey_id = survey["survey_id"]
	sleek.upload_survey(survey)
	#test wrong inputs	
	am_check = "10:00am" 
	pm_check = "05:00pm" 
	bad_am = "19dasam"
	bad_pm = "19daspm"
	#bad inputs
	#try to join a survey that does not exist	
	bad_survey_id = "something"
	ret = sleek.join_survey(["join", bad_survey_id,am_check,pm_check], context)
	assert status.SURVEY_UNKNOWN.format(bad_survey_id.upper()) == ret
	#invalid am time
	ret = sleek.join_survey(["join", survey_id, bad_am], context) 
	assert ret == status.INVALID_TIME.format(bad_am)
	#invalid pm time
	ret = sleek.join_survey(["join", survey_id, bad_pm], context) 
	assert ret == status.INVALID_TIME.format(bad_pm)

	#valid AM time but *invalid* PM time
	ret = sleek.join_survey(["join", survey_id, am_check, bad_am], context) 
	assert ret == status.INVALID_TIME.format(bad_am)

	#*valid* AM time but invalid PM time
	ret = sleek.join_survey(["join", survey_id, bad_pm, pm_check], context) 
	assert ret == status.INVALID_TIME.format(bad_pm)

	#check that user has not joined the sleep survey
	data = backend.list_surveys(DB_path, some_user)
	assert data == []
	ret = sleek.join_survey(["join",survey_id], context)
	assert status.SURVEY_JOIN_OK.format(survey_id) == ret
	data = backend.list_surveys(DB_path, some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	#joining the same survey again
	ret = sleek.join_survey(["join",survey_id, am_check, pm_check], context) 
	assert ret == status.SURVEY_IS_SUBSCRIBED.format(survey_id.upper())

	#leave survey
	backend.leave_survey(DB_path, some_user, survey_id)
	
	#join survey with AM reminder
	ret = sleek.join_survey(["join",survey_id, am_check], context).split("\n")	
	assert status.SURVEY_JOIN_OK.format(survey_id) == ret[0]			
	assert status.REMINDER_OK.format(survey_id, am_check) == ret[1]
	data = backend.list_surveys(DB_path, some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == am_check
	assert data[3] == None
	backend.leave_survey(DB_path, some_user, survey_id)

	#join survey with PM reminder
	ret = sleek.join_survey(["join",survey_id, pm_check], context).split("\n")	
	assert status.SURVEY_JOIN_OK.format(survey_id) == ret[0]	
	assert status.REMINDER_OK.format(survey_id, pm_check) == ret[1]	
	data = backend.list_surveys(DB_path, some_user)[0]	
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == None
	assert data[3] == pm_check
	backend.leave_survey(DB_path, some_user, survey_id)

	#join survey with both reminders
	ret = sleek.join_survey(["join",survey_id, pm_check, am_check], context).split("\n")
	assert status.SURVEY_JOIN_OK.format(survey_id, survey_id) == ret[0]	
	assert status.REMINDER_OK_2.format(survey_id, am_check, 
												  pm_check) == ret[1]		
	data = backend.list_surveys(DB_path, some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == am_check
	assert data[3] == pm_check
	backend.leave_survey(DB_path, some_user, survey_id)

def test_leave():
	sleek = Sleek4Slack(DB_path, init_backend=True)		
	# sleek.connect(api_token)		
	#add sleep and stress surveys
	survey = json.load(open("DATA/surveys/sleep.json", 'r'))					
	sleek.upload_survey(survey)
	survey2 = json.load(open("DATA/surveys/stress.json", 'r'))					
	sleek.upload_survey(survey2)
	#try to leave a survey that does not exist
	bad_survey_id = "saleep"
	ret = sleek.leave_survey(["leave",bad_survey_id], context)
	assert ret == status.SURVEY_UNKNOWN.format(bad_survey_id.upper())
	#try to leave stress survey (it was not joined)
	bad_survey_id = "stress"
	ret = sleek.leave_survey(["leave",bad_survey_id], context)
	assert ret == status.SURVEY_NOT_SUBSCRIBED.format(bad_survey_id.upper())
	#join sleep survey	
	survey_id = "sleep"
	ret = sleek.join_survey(["join", survey_id], context)
	assert status.SURVEY_JOIN_OK.format(survey_id) == ret
	data = backend.list_surveys(DB_path, some_user)[0]
	assert data[0] == some_user
	assert data[1] == "sleep"	
	#try to leave stress survey 
	ret = sleek.leave_survey(["leave",survey_id], context)
	assert ret == status.SURVEY_LEAVE_OK.format(survey_id.upper())
	for x in backend.list_surveys(DB_path, some_user):
		assert "sleep" not in x[0]
	
def test_reminder():
	sleek = Sleek4Slack(DB_path, init_backend=True)		
	# sleek.connect(api_token)		
	survey_id = "sleep"
	survey = json.load(open("DATA/surveys/sleep.json", 'r'))				
	survey_id = survey["survey_id"]
	sleek.upload_survey(survey)	
	am_check = "10:00am"
	pm_check = "5:00pm"
	#join survey
	ret = sleek.join_survey(["join",survey_id], context)	
	data = backend.list_surveys(DB_path, some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == None
	assert data[3] == None

	#try to reschedule
	new_am_check="6:00am"
	new_pm_check="6:20pm"
	bad_am="6:am"
	bad_pm=":20pm"
	#bad inputs

	#invalid am time
	ret = sleek.remind_survey(["reminder", survey_id, bad_am], context) 
	assert ret == status.INVALID_TIME.format(bad_am)
	#invalid pm time
	ret = sleek.remind_survey(["reminder", survey_id, bad_pm], context) 
	assert ret == status.INVALID_TIME.format(bad_pm)
	
	#valid AM time but *invalid* PM time
	ret = sleek.remind_survey(["reminder", survey_id, am_check, bad_am], context) 
	assert ret == status.INVALID_TIME.format(bad_am)

	#*valid* AM time but invalid PM time
	ret = sleek.remind_survey(["reminder", survey_id, bad_pm, pm_check], context) 
	assert ret == status.INVALID_TIME.format(bad_pm)
	
	#new am reminder
	ret = sleek.remind_survey(["reminder",survey_id, new_am_check], context) 
	assert ret == status.REMINDER_OK.format(survey_id, new_am_check)
	data = backend.list_surveys(DB_path, some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == new_am_check
	assert data[3] == None

	#new pm reminder
	ret = sleek.remind_survey(["reminder",survey_id, new_pm_check], context) 
	assert ret == status.REMINDER_OK.format(survey_id, new_pm_check)
	data = backend.list_surveys(DB_path, some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == new_am_check
	assert data[3] == new_pm_check

	#old reminders
	ret = sleek.remind_survey(["reminder",survey_id, am_check, pm_check], context) 
	assert ret == status.REMINDER_OK_2.format(survey_id, am_check, pm_check)
	data = backend.list_surveys(DB_path, some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == am_check
	assert data[3] == pm_check

def test_report_and_delete_answers():
	sleek = Sleek4Slack(DB_path, init_backend=True)		
	# sleek.connect(api_token)			
	#add sleep and stress surveys	
	sleek.upload_survey(json.load(open("DATA/surveys/sleep.json", 'r')))	
	sleek.upload_survey(json.load(open("DATA/surveys/stress.json", 'r')))	
	user_id="u1"
	survey_id="sleep"
	am_check = "10:00am"
	pm_check = "5:00pm"
	assert sleek.join_survey(["join","sleep", am_check, pm_check], context)[0]
	assert sleek.join_survey(["join","stress", am_check, pm_check], context)[0]
	#add two responses
	resp_id_1 = backend.save_response(DB_path, user_id, survey_id, 100, {"sleep_hours":9,"sleep_quality":5})
	resp_id_2 = backend.save_response(DB_path, user_id, survey_id, 200, {"sleep_hours":5,"sleep_quality":2})
	
	#check responses are there
	resp = backend.get_report(DB_path, user_id, survey_id)	
	assert resp[0] == (resp_id_2, user_id, '200', '5', '2')
	assert resp[1] == (resp_id_1, user_id, '100', '9', '5')
	backend.delete_answers(DB_path, user_id, survey_id)
	resp = backend.get_report(DB_path, user_id, survey_id)
	assert resp == []

def test_survey():
	sleek = Sleek4Slack(DB_path, init_backend=True)		
	# sleek.connect(api_token)			
	#add survey
	survey_sleep = json.load(open("DATA/surveys/sleep.json", 'r'))
	survey_stress = json.load(open("DATA/surveys/stress.json", 'r'))

	sleek.upload_survey(survey_sleep)		
	sleek.upload_survey(survey_stress)			
	survey_id="sleep"
	am_check = "10:00am"
	pm_check = "5:00pm"
	sleek.join_survey(["join",survey_id, am_check, pm_check], context)	
	#check that there is no response yet
	resp = backend.get_response(DB_path, some_user, survey_id, 1)
	assert resp == []
	#engage
	#survey does not exist
	resp = sleek.open_survey(["survey","bad_survey"], context)
	assert resp == status.SURVEY_UNKNOWN.format("BAD_SURVEY")
	#user did not subscribe to this survey
	resp = sleek.open_survey(["survey","stress"], context)
	assert resp == status.SURVEY_NOT_SUBSCRIBED.format("STRESS") + " " + status.PLEASE_SUBSCRIBE		
	
	survey = sleek.open_survey(["survey","sleep"], context, display=False)
	assert survey == survey_sleep
	#check that a survey thread is created
	assert sleek.survey_threads[context["thread_ts"]] == (some_user, survey_id, None)

def test_save_answer():
	sleek = Sleek4Slack(DB_path, init_backend=True)		
	# sleek.connect(api_token)			
	#add survey
	survey_sleep = json.load(open("DATA/surveys/sleep.json", 'r'))
	survey_stress = json.load(open("DATA/surveys/stress.json", 'r'))

	sleek.upload_survey(survey_sleep)		
	sleek.upload_survey(survey_stress)			
	survey_id="sleep"
	am_check = "10:00am"
	pm_check = "5:00pm"
	sleek.join_survey(["join",survey_id, am_check, pm_check], context)	
	survey = sleek.open_survey(["survey","sleep"], context, display=False)
	assert survey == survey_sleep
	#check that a survey thread is created
	assert sleek.survey_threads[context["thread_ts"]] == (some_user, survey_id, None)

	#incorrect number of answers
	bad_resp = "1"
	resp = sleek.get_answer(context["thread_ts"], bad_resp )	
	assert resp == status.ANSWERS_TOO_FEW.format(2, 1)		

	bad_resp = "1 2 3 4"
	resp = sleek.get_answer(context["thread_ts"], bad_resp )	
	assert resp == status.ANSWERS_TOO_MANY.format(2, 4)		

	#invalid choice 1
	bad_resp = "-1 2"
	bad_q_id = "sleep_hours"
	#sleep_quality
	resp = sleek.get_answer(context["thread_ts"], bad_resp )	
	assert resp == status.ANSWERS_BAD_CHOICE.format(bad_q_id)
	#invalid choice 2
	bad_resp = "1 20"
	bad_q_id = "sleep_quality"
	#sleep_quality
	resp = sleek.get_answer(context["thread_ts"], bad_resp )	
	assert resp == status.ANSWERS_BAD_CHOICE.format(bad_q_id), resp

	good_resp = "1 2"		
	resp = sleek.get_answer(context["thread_ts"], good_resp )	
	resp = sleek.save_answer(context["thread_ts"], 100)
	assert resp == status.ANSWERS_SAVE_OK
	#ok



if __name__ == "__main__":
	pass
		# test_join()
	



