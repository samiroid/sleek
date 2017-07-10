from ipdb import set_trace
import json
import pytest
from datetime import datetime
import sys

#sleek
sys.path.append("sleek")
from sleek import Sleek, Sleek4Slack, out
from sleek import LocalBackend as Backend

back_cfg = {
		"local_DB":"DATA/test_slack.db"
		}

user_id="SILVIO"
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
	my_backend = Backend(back_cfg, create=True)
	sleek = Sleek4Slack(my_backend)	
	assert len(sleek.current_surveys) == 0
	survey = json.load(open("DATA/surveys/sleep.json", 'r'))				
	my_backend.create_survey(survey)
	sleek = Sleek4Slack(my_backend)
	assert len(sleek.current_surveys) == 1
	assert my_backend.get_survey("sleep") is not None
	#try to create the same survey
	with pytest.raises(RuntimeError):
		my_backend.create_survey(survey)
	
def test_join():
	my_backend = Backend(back_cfg, create=True)	
	sleep_survey = json.load(open("DATA/surveys/sleep.json", 'r'))				
	my_backend.create_survey(sleep_survey)
	sleek = Sleek4Slack(my_backend)		
	survey_id = sleep_survey["id"]
	#test wrong inputs	
	am_check = "10:00am" 
	pm_check = "05:00pm" 
	bad_am = "19dasam"
	bad_pm = "19daspm"
	#bad inputs
	#try to join a survey that does not exist	
	bad_survey_id = "something"
	ret = sleek.join(["join", bad_survey_id,am_check,pm_check], context)
	assert out.SURVEY_UNKNOWN.format(bad_survey_id.upper()) == ret
	#invalid am time
	ret = sleek.join(["join", survey_id, bad_am], context) 
	assert ret == out.INVALID_TIME.format(bad_am)
	#invalid pm time
	ret = sleek.join(["join", survey_id, bad_pm], context) 
	assert ret == out.INVALID_TIME.format(bad_pm)

	#valid AM time but *invalid* PM time
	ret = sleek.join(["join", survey_id, am_check, bad_am], context) 
	assert ret == out.INVALID_TIME.format(bad_am)

	#*valid* AM time but invalid PM time
	ret = sleek.join(["join", survey_id, bad_pm, pm_check], context) 
	assert ret == out.INVALID_TIME.format(bad_pm)

	#check that user has not joined the sleep survey
	data = my_backend.list_surveys(some_user)
	assert data == []
	ret = sleek.join(["join",survey_id], context)
	assert out.SURVEY_JOIN_OK.format(survey_id.upper()) == ret[1]
	data = my_backend.list_surveys(some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	#joining the same survey again
	ret = sleek.join(["join",survey_id, am_check, pm_check], context) 
	assert ret == out.SURVEY_IS_SUBSCRIBED.format(survey_id.upper())

	#leave survey
	my_backend.leave_survey(some_user, survey_id)
	
	#join survey with AM reminder
	ret = sleek.join(["join",survey_id, am_check], context)	
	assert out.SURVEY_JOIN_OK.format(survey_id.upper()) == ret[1]			
	assert out.REMINDER_OK.format(survey_id.upper(), am_check.upper()) == ret[2]
	data = my_backend.list_surveys(some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == am_check.upper()
	assert data[3] == None
	my_backend.leave_survey(some_user, survey_id)

	#join survey with PM reminder
	ret = sleek.join(["join",survey_id, pm_check], context)	
	assert out.SURVEY_JOIN_OK.format(survey_id.upper()) == ret[1]	
	assert out.REMINDER_OK.format(survey_id.upper(), pm_check.upper()) == ret[2]	
	data = my_backend.list_surveys(some_user)[0]	
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == None
	assert data[3] == pm_check.upper()
	my_backend.leave_survey(some_user, survey_id)

	#join survey with both reminders
	ret = sleek.join(["join",survey_id, pm_check, am_check], context)
	assert out.SURVEY_JOIN_OK.format(survey_id.upper()) == ret[1]	
	assert out.REMINDER_OK_2.format(survey_id.upper(), am_check.upper(), 
												  pm_check.upper()) == ret[2]		
	data = my_backend.list_surveys(some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == am_check.upper()
	assert data[3] == pm_check.upper()
	my_backend.leave_survey(some_user, survey_id)

def test_leave():
	my_backend = Backend(back_cfg, create=True)	
	#add sleep and stress surveys
	sleep_survey = json.load(open("DATA/surveys/sleep.json", 'r'))					
	my_backend.create_survey(sleep_survey)
	stress_survey = json.load(open("DATA/surveys/stress.json", 'r'))					
	my_backend.create_survey(stress_survey)
	sleek = Sleek4Slack(my_backend)		
	#try to leave a survey that does not exist
	bad_survey_id = "saleep"
	ret = sleek.leave(["leave",bad_survey_id], context)
	assert ret == out.SURVEY_UNKNOWN.format(bad_survey_id.upper())
	#try to leave stress survey (it was not joined)
	bad_survey_id = stress_survey["id"]
	ret = sleek.leave(["leave",bad_survey_id], context)
	assert ret == out.SURVEY_NOT_SUBSCRIBED.format(bad_survey_id.upper())
	#join sleep survey	
	survey_id = sleep_survey["id"]
	ret = sleek.join(["join", survey_id], context)
	assert out.SURVEY_JOIN_OK.format(survey_id.upper()) == ret[1]
	data = my_backend.list_surveys(some_user)[0]
	assert data[0] == some_user
	assert data[1] == "sleep"	
	#try to leave stress survey 
	ret = sleek.leave(["leave",survey_id], context)
	assert out.SURVEY_LEAVE_OK.format(survey_id.upper()) == ret[1]
	for x in my_backend.list_surveys(some_user):
		assert "sleep" not in x[0]
	
def test_reminder():
	my_backend = Backend(back_cfg, create=True)	
	sleep_survey = json.load(open("DATA/surveys/sleep.json", 'r'))				
	survey_id = sleep_survey["id"]
	my_backend.create_survey(sleep_survey)	
	sleek = Sleek4Slack(my_backend)		
	am_check = "10:00am"
	pm_check = "05:00pm"
	#join survey
	ret = sleek.join(["join",survey_id], context)	
	data = my_backend.list_surveys(some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == None
	assert data[3] == None

	#try to reschedule
	new_am_check="06:00am"
	new_pm_check="06:20pm"
	bad_am="6:am"
	bad_pm=":20pm"
	#bad inputs

	#invalid am time
	ret = sleek.reminder(["reminder", survey_id, bad_am], context) 
	assert out.INVALID_TIME.format(bad_am) == ret
	#invalid pm time
	ret = sleek.reminder(["reminder", survey_id, bad_pm], context) 
	assert out.INVALID_TIME.format(bad_pm) == ret
	
	#valid AM time but *invalid* PM time
	ret = sleek.reminder(["reminder", survey_id, am_check, bad_am], context) 
	assert out.INVALID_TIME.format(bad_am) == ret

	#*valid* AM time but invalid PM time
	ret = sleek.reminder(["reminder", survey_id, bad_pm, pm_check], context) 
	assert out.INVALID_TIME.format(bad_pm) == ret
	
	#new am reminder
	ret = sleek.reminder(["reminder",survey_id, new_am_check], context) 
	assert out.REMINDER_OK.format(survey_id.upper(), new_am_check.upper()) == ret[1]
	data = my_backend.list_surveys(some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == new_am_check.upper()
	assert data[3] == None

	#new pm reminder
	ret = sleek.reminder(["reminder",survey_id, new_pm_check], context) 
	assert out.REMINDER_OK.format(survey_id.upper(), new_pm_check.upper()) == ret[1]
	data = my_backend.list_surveys(some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == new_am_check.upper()
	assert data[3] == new_pm_check.upper()

	#old reminders
	ret = sleek.reminder(["reminder",survey_id, am_check, pm_check], context) 
	assert out.REMINDER_OK_2.format(survey_id.upper(), am_check.upper(), pm_check.upper()) == ret[1]
	data = my_backend.list_surveys(some_user)[0]
	assert data[0] == some_user
	assert data[1] == survey_id
	assert data[2] == am_check.upper()
	assert data[3] == pm_check.upper()

def test_report_and_delete():
	my_backend = Backend(back_cfg, create=True)		
	#add sleep and stress surveys	
	my_backend.create_survey(json.load(open("DATA/surveys/sleep.json", 'r')))	
	my_backend.create_survey(json.load(open("DATA/surveys/stress.json", 'r')))	
	sleek = Sleek4Slack(my_backend)		

	survey_id="sleep"
	am_check = "10:00am"
	pm_check = "5:00pm"
	assert sleek.join(["join","sleep", am_check, pm_check], context)[0]
	assert sleek.join(["join","stress", am_check, pm_check], context)[0]
	#add two responses
	resp_id_1 = my_backend.save_answer(user_id, survey_id, {"sleep_hours":9,"sleep_quality":5,"ts":100})
	resp_id_2 = my_backend.save_answer(user_id, survey_id, {"sleep_hours":5,"sleep_quality":2,"ts":200,"notes":"some note"})
	
	#check responses are there
	resp = my_backend.get_report(user_id, survey_id)	
	assert resp[0] == (resp_id_2, user_id, '200', '5', '2', "some note")
	assert resp[1] == (resp_id_1, user_id, '100', '9', '5', None)
	my_backend.delete_answers(user_id, survey_id)
	resp = my_backend.get_report(user_id, survey_id)
	assert resp == []

def test_survey():
	my_backend = Backend(back_cfg, create=True)		
	#add survey
	survey_sleep = json.load(open("DATA/surveys/sleep.json", 'r'))
	survey_stress = json.load(open("DATA/surveys/stress.json", 'r'))
	my_backend.create_survey(survey_sleep)		
	my_backend.create_survey(survey_stress)			
	sleek = Sleek4Slack(my_backend)		
	survey_id= survey_sleep["id"]
	am_check = "10:00am"
	pm_check = "5:00pm"
	sleek.join(["join",survey_id, am_check, pm_check], context)	
	#check that there is no response yet
	resp = my_backend.get_report(user_id, survey_id)	
	assert resp == []
	
	#survey does not exist
	resp = sleek.survey(["survey","bad_survey"], context)
	assert resp == out.SURVEY_UNKNOWN.format("BAD_SURVEY")
	#user did not subscribe to this survey
	resp = sleek.survey(["survey","stress"], context)
	assert resp == out.SURVEY_NOT_SUBSCRIBED.format("STRESS") 
	
	survey = sleek.survey(["survey","sleep"], context, display=False)
	assert survey == survey_sleep
	#check that a survey thread is created
	assert sleek.survey_threads[context["thread_ts"]] == (some_user, survey_id, None)

def test_save_answer():
	my_backend = Backend(back_cfg, create=True)	
	survey_sleep = json.load(open("DATA/surveys/sleep.json", 'r'))
	survey_stress = json.load(open("DATA/surveys/stress.json", 'r'))
	my_backend.create_survey(survey_sleep)		
	my_backend.create_survey(survey_stress)			
	sleek = Sleek4Slack(my_backend)		
	survey_id="sleep"
	am_check = "10:00am"
	pm_check = "5:00pm"
	sleek.join(["join",survey_id, am_check, pm_check], context)	
	survey = sleek.survey(["survey","sleep"], context, display=False)
	assert survey == survey_sleep
	#check that a survey thread is created
	assert sleek.survey_threads[context["thread_ts"]] == (some_user, survey_id, None)

	#incorrect number of answers
	bad_resp = "1"
	resp = sleek.parse_answer(context["thread_ts"], bad_resp )	
	assert resp == out.ANSWERS_TOO_FEW.format(2, 1)		

	bad_resp = "1 2 3 4"
	resp = sleek.parse_answer(context["thread_ts"], bad_resp )	
	assert resp == out.ANSWERS_TOO_MANY.format(2, 4)		

	#invalid choice 1
	bad_resp = "-1 2"
	bad_q_id = "sleep_hours"
	#sleep_quality
	resp = sleek.parse_answer(context["thread_ts"], bad_resp )	
	assert resp == out.ANSWERS_BAD_CHOICE.format(bad_q_id)
	#invalid choice 2
	bad_resp = "1 20"
	bad_q_id = "sleep_quality"
	#sleep_quality
	resp = sleek.parse_answer(context["thread_ts"], bad_resp )	
	assert resp == out.ANSWERS_BAD_CHOICE.format(bad_q_id), resp

	good_resp = "1 2"		
	resp = sleek.parse_answer(context["thread_ts"], good_resp )	
	resp = sleek.save_answer(context["thread_ts"])
	assert resp == out.ANSWERS_SAVE_OK
	#ok



if __name__ == "__main__":
	pass
		# test_join()
	



