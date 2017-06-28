from datetime import datetime
from ipdb import set_trace
import json
import os
import pytest
import sqlite_backend as backend
from sleek_4_slack import Sleek4Slack

DB_path="DATA/test_slack.db"

try:
	os.remove(DB_path)
except OSError:
	pass

bot_name="dude"
api_token = os.environ.get('SLACK_BOT_TOKEN')
silvio="U5TCJ682Z"
context = {"user":silvio}

# def test_load_surveys():
# 	sleek = Sleek4Slack(DB_path, init_backend=True)	
# 	assert len(sleek.surveys) == 0
# 	survey = json.load(open("DATA/surveys/sleep.json", 'r'))				
# 	assert sleek.upload_survey(survey)
# 	sleek.connect(api_token)	
# 	# set_trace()
# 	assert backend.get_survey(DB_path, "sleep") is not None
# 	assert not sleek.upload_survey(survey)
# 	os.remove(DB_path)

# def test_join():
# 	sleek = Sleek4Slack(DB_path, init_backend=True)		
# 	sleek.connect(api_token)		
# 	survey_id = "sleep"
# 	survey = json.load(open("DATA/surveys/sleep.json", 'r'))				
# 	survey_id = survey["survey_id"]
# 	sleek.upload_survey(survey)
# 	#test wrong inputs	
# 	am_check = "10:00AM"
# 	pm_check = "5:00PM"
# 	#bad inputs
# 	ret = sleek.join_survey(["join", survey_id, "10", "10"], context) 
# 	assert not ret[0], ret
# 	ret = sleek.join_survey(["join", survey_id, am_check, "10"], context) 
# 	assert not ret[0], ret
# 	ret = sleek.join_survey(["join", survey_id, "10", pm_check], context) 
# 	assert not ret[0], ret
# 	#try to join a survey that does not exist	
# 	ret = sleek.join_survey(["join","something",am_check,pm_check], context)
# 	assert not ret[0], ret
# 	#check that user has not joined the sleep survey
# 	data = backend.list_surveys(DB_path, silvio)
# 	assert data == []
# 	ret = sleek.join_survey(["join",survey_id, am_check, pm_check], context)
# 	assert ret[0], ret
# 	data = backend.list_surveys(DB_path, silvio)[0]
# 	assert data[0] == silvio
# 	assert data[1] == survey_id
# 	#joining the same survey again
# 	ret = sleek.join_survey(["join",survey_id, am_check, pm_check], context) 
# 	assert not ret[0], ret

# def test_leave():
# 	sleek = Sleek4Slack(DB_path, init_backend=True)		
# 	sleek.connect(api_token)		
# 	#add sleep and stress surveys
# 	survey = json.load(open("DATA/surveys/sleep.json", 'r'))					
# 	sleek.upload_survey(survey)
# 	survey2 = json.load(open("DATA/surveys/stress.json", 'r'))					
# 	sleek.upload_survey(survey2)
# 	#try to leave a survey that does not exist
# 	ret = sleek.leave_survey(["leave","saleep"], context)
# 	assert not ret[0], ret	
# 	#try to leave stress survey (it was not joined)
# 	ret = sleek.leave_survey(["leave","stress"], context)
# 	assert not ret[0], ret
# 	#join sleep survey
# 	am_check = "10:00AM"
# 	pm_check = "5:00PM"
# 	ret = sleek.join_survey(["join","sleep", am_check, pm_check], context)
# 	assert ret[0], ret
# 	data = backend.list_surveys(DB_path, silvio)[0]
# 	assert data[0] == silvio
# 	assert data[1] == "sleep"	
# 	#try to leave stress survey 
# 	ret = sleek.leave_survey(["leave","sleep"], context)
# 	assert ret[0], ret
# 	for x in backend.list_surveys(DB_path, silvio):
# 		assert "sleep" not in x[0]
	
# def test_list_surveys():
# 	sleek = Sleek4Slack(DB_path, init_backend=True)		
# 	sleek.connect(api_token)		
# 	surveys = sleek.list_surveys(["list"], context)
# 	assert len(surveys) == 0, surveys
# 	#add sleep and stress surveys	
# 	sleek.upload_survey(json.load(open("DATA/surveys/sleep.json", 'r')))	
# 	sleek.upload_survey(json.load(open("DATA/surveys/stress.json", 'r')))
# 	surveys = sleek.list_surveys(["list"], context)
# 	assert len(surveys) == 2, surveys
# 	assert surveys["sleep"] == False
# 	assert surveys["stress"] == False
# 	am_check = "10:00AM"
# 	pm_check = "5:00PM"
# 	assert sleek.join_survey(["join","sleep", am_check, pm_check], context)[0]
# 	surveys = sleek.list_surveys(["list"], context)
# 	assert len(surveys) == 2, surveys
# 	assert surveys["sleep"] == True, surveys
# 	assert surveys["stress"] == False, surveys

# def test_schedule():
# 	sleek = Sleek4Slack(DB_path, init_backend=True)		
# 	sleek.connect(api_token)		
# 	survey_id = "sleep"
# 	survey = json.load(open("DATA/surveys/sleep.json", 'r'))				
# 	survey_id = survey["survey_id"]
# 	sleek.upload_survey(survey)	
# 	am_check = "10:00AM"
# 	pm_check = "5:00PM"
# 	#join survey
# 	ret = sleek.join_survey(["join",survey_id, am_check, pm_check], context)
# 	assert ret[0], ret
# 	data = backend.list_surveys(DB_path, silvio)[0]
# 	assert data[0] == silvio
# 	assert data[1] == survey_id
# 	assert data[2] == str(datetime.strptime(am_check , '%I:%M%p').time())
# 	assert data[3] == str(datetime.strptime(pm_check , '%I:%M%p').time())

# 	#try to reschedule
# 	new_am_check="6:00AM"
# 	new_pm_check="6:20PM"
# 	#bad inputs
# 	ret = sleek.schedule_survey(["schedule", survey_id, "10", "10"], context) 
# 	assert not ret[0], ret
# 	ret = sleek.schedule_survey(["schedule", survey_id, am_check, "10"], context) 
# 	assert not ret[0], ret
# 	ret = sleek.schedule_survey(["schedule", survey_id, "10", pm_check], context) 
# 	assert not ret[0], ret
# 	ret = sleek.schedule_survey(["schedule",survey_id, new_am_check, new_pm_check], context) 
# 	assert ret[0], ret

# 	data = backend.list_surveys(DB_path, silvio)[0]
# 	assert data[0] == silvio
# 	assert data[1] == survey_id
# 	assert data[2] == str(datetime.strptime(new_am_check , '%I:%M%p').time())
# 	assert data[3] == str(datetime.strptime(new_pm_check , '%I:%M%p').time())

# def test_delete_answers():
# 	sleek = Sleek4Slack(DB_path, init_backend=True)		
# 	sleek.connect(api_token)			
# 	#add sleep and stress surveys	
# 	sleek.upload_survey(json.load(open("DATA/surveys/sleep.json", 'r')))	
# 	sleek.upload_survey(json.load(open("DATA/surveys/stress.json", 'r')))	
# 	user_id="u1"
# 	survey_id="sleep"
# 	am_check = "10:00AM"
# 	pm_check = "5:00PM"
# 	assert sleek.join_survey(["join","sleep", am_check, pm_check], context)[0]
# 	assert sleek.join_survey(["join","stress", am_check, pm_check], context)[0]
# 	#add two responses
# 	resp_id_1 = backend.new_response(DB_path, user_id, survey_id, 100)
# 	backend.save_response(DB_path, survey_id, user_id, resp_id_1, {"sleep_hours":9,"sleep_quality":5})
# 	backend.close_response(DB_path, user_id, survey_id, resp_id_1)

# 	resp_id_2 = backend.new_response(DB_path, user_id, survey_id, 200)
# 	backend.save_response(DB_path, survey_id, user_id, resp_id_2, {"sleep_hours":5,"sleep_quality":2})
# 	backend.close_response(DB_path, user_id, survey_id, resp_id_2)
# 	#check responses are there
# 	resp = backend.get_report(DB_path, user_id, survey_id)	
# 	assert resp[0] == (resp_id_2, user_id, '200', '5', '2', 1)
# 	assert resp[1] == (resp_id_1, user_id, '100', '9', '5', 1)
# 	backend.delete_responses(DB_path, user_id, survey_id)
# 	resp = backend.get_report(DB_path, user_id, survey_id)
# 	assert resp == []

# # def test_pause_resume():
# # 	assert True == False

# def test_report():
# 	sleek = Sleek4Slack(DB_path, init_backend=True)		
# 	sleek.connect(api_token)			
# 	#add sleep and stress surveys	
# 	sleek.upload_survey(json.load(open("DATA/surveys/sleep.json", 'r')))	
# 	sleek.upload_survey(json.load(open("DATA/surveys/stress.json", 'r')))	
# 	user_id="u1"
# 	survey_id="sleep"
# 	am_check = "10:00AM"
# 	pm_check = "5:00PM"
# 	assert sleek.join_survey(["join","sleep", am_check, pm_check], context)[0]
# 	assert sleek.join_survey(["join","stress", am_check, pm_check], context)[0]
# 	#add two responses
# 	resp_id_1 = backend.new_response(DB_path, user_id, survey_id, 100)
# 	backend.save_response(DB_path, survey_id, user_id, resp_id_1, {"sleep_hours":9,"sleep_quality":5})
# 	backend.close_response(DB_path, user_id, survey_id, resp_id_1)

# 	resp_id_2 = backend.new_response(DB_path, user_id, survey_id, 200)
# 	backend.save_response(DB_path, survey_id, user_id, resp_id_2, {"sleep_hours":5,"sleep_quality":2})
# 	backend.close_response(DB_path, user_id, survey_id, resp_id_2)
# 	#check responses are there
# 	resp = backend.get_report(DB_path, user_id, survey_id)	
# 	assert resp[0] == (resp_id_2, user_id, '200', '5', '2', 1)
# 	assert resp[1] == (resp_id_1, user_id, '100', '9', '5', 1)
# 	backend.delete_responses(DB_path, user_id, survey_id)
# 	resp = backend.get_report(DB_path, user_id, survey_id)
# 	assert resp == []

def test_engage():
	sleek = Sleek4Slack(DB_path, init_backend=True)		
	sleek.connect(api_token)			
	#add survey
	survey = json.load(open("DATA/surveys/sleep.json", 'r'))
	sleek.upload_survey(survey)		
	user_id="u1"
	survey_id="sleep"
	am_check = "10:00AM"
	pm_check = "5:00PM"
	assert sleek.join_survey(["join","sleep", am_check, pm_check], context)[0]
	#assert sleek.join_survey(["join","stress", am_check, pm_check], context)[0]
	#check that there no responses yet
	resp = backend.get_response(DB_path, user_id, survey_id, 1)
	assert resp == []
	#engage
	question, response_id = sleek.engage(user_id, survey_id)
	assert response_id == 1
	assert question["id"] == survey["survey"][0]["id"]
	#check that a new response was created
	resp = backend.get_response(DB_path, user_id, survey_id, 1)
	assert resp[0] == response_id
	assert resp[1] == user_id
	assert resp[3] == None
	assert resp[4] == None
	#engage again and check that the same question is returned (it was not answered yet)
	question, response_id = sleek.engage(user_id, survey_id)
	assert response_id == 1
	assert question["id"] == survey["survey"][0]["id"]
	#get answer
	question, response_id = sleek.engage(user_id, survey_id)
	assert response_id == 1
	assert question["id"] == survey["survey"][0]["id"]


def test_save_response():
	sleek = Sleek4Slack(DB_path, init_backend=True)		
	sleek.connect(api_token)			
	#add survey
	survey = json.load(open("DATA/surveys/sleep.json", 'r'))
	sleek.upload_survey(survey)		
	user_id="u1"
	survey_id="sleep"
	am_check = "10:00AM"
	pm_check = "5:00PM"
	assert sleek.join_survey(["join","sleep", am_check, pm_check], context)[0]
	#check that there no responses yet
	resp = backend.get_response(DB_path, user_id, survey_id, 1)
	assert resp == []
	#engage
	question_1, resp_id_1 = sleek.engage(user_id, survey_id)
	assert resp_id_1 == 1
	assert question_1["id"] == survey["survey"][0]["id"]
	#check that a new response was created
	response = backend.get_response(DB_path, user_id, survey_id, resp_id_1)
	assert response[0] == resp_id_1
	assert response[1] == user_id
	assert response[3] == None
	assert response[4] == None	
	assert response[5] == 0
	#answer question_1 (sleep hours)
	sleek.answer(user_id, survey_id, question_1["id"], resp_id_1, 8)
	#check that response was updated
	response = backend.get_response(DB_path, user_id, survey_id, resp_id_1)
	assert response[0] == resp_id_1
	assert response[1] == user_id
	assert response[3] == '8'
	assert response[4] == None	
	assert response[5] == 0

	#engage again (new question)	
	question_2, resp_id_2 = sleek.engage(user_id, survey_id)
	assert resp_id_1 == resp_id_1 #this is the same response
	assert question_2["id"] == survey["survey"][1]["id"]
	#answer question_2 (sleep quality)
	sleek.answer(user_id, survey_id, question_2["id"], resp_id_2, 2)
	#check that response was updated
	resp = backend.get_response(DB_path, user_id, survey_id, resp_id_2)
	assert resp[0] == resp_id_2
	assert resp[1] == user_id
	assert resp[3] == "8"
	assert resp[4] == "2"
	assert resp[5] == 1 #response should be closed
	
if __name__ == "__main__":
	sleek = Sleek4Slack(DB_path, init_backend=True)		
	sleek.connect(api_token)			
	#add survey
	survey = json.load(open("DATA/surveys/sleep.json", 'r'))
	sleek.upload_survey(survey)		
	user_id="u1"
	survey_id="sleep"
	am_check = "10:00AM"
	pm_check = "5:00PM"
	assert sleek.join_survey(["join","sleep", am_check, pm_check], context)[0]
	#check that there no responses yet
	resp = backend.get_response(DB_path, user_id, survey_id, 1)
	assert resp == []
	#engage
	question_1, resp_id_1 = sleek.engage(user_id, survey_id)
	assert resp_id_1 == 1
	assert question_1["id"] == survey["survey"][0]["id"]
	#check that a new response was created
	response = backend.get_response(DB_path, user_id, survey_id, resp_id_1)
	assert response[0] == resp_id_1
	assert response[1] == user_id
	assert response[3] == None
	assert response[4] == None	
	assert response[5] == 0
	#answer question_1 (sleep hours)
	sleek.answer(user_id, survey_id, question_1["id"], resp_id_1, 8)
	#check that response was updated
	response = backend.get_response(DB_path, user_id, survey_id, resp_id_1)
	assert response[0] == resp_id_1
	assert response[1] == user_id
	assert response[3] == '8'
	assert response[4] == None	
	assert response[5] == 0

	#engage again (new question)	
	question_2, resp_id_2 = sleek.engage(user_id, survey_id)
	assert resp_id_1 == resp_id_1 #this is the same response
	assert question_2["id"] == survey["survey"][1]["id"]
	#answer question_2 (sleep quality)
	sleek.answer(user_id, survey_id, question_2["id"], resp_id_2, 2)
	#check that response was updated
	resp = backend.get_response(DB_path, user_id, survey_id, resp_id_2)
	assert resp[0] == resp_id_2
	assert resp[1] == user_id
	assert resp[3] == "8"
	assert resp[4] == "2"
	assert resp[5] == 1 #response should be closed



