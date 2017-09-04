# -*- coding: UTF-8 -*-
from ipdb import set_trace
import pytest
import sys
#sleek
sys.path.insert(0,'..')
from sleek import Sleek, SleekMsg, User, Survey, Backend
import sleek

DB_path="test.db"
confs={"backend_type":"local",
	   "local_DB":DB_path}

user_id="id1"
dummy_user_list = {"silvio":"id1",
				   "alice":"id2",
				   "bob":"id3"}

survey_id="sleep"
sleep_survey = { "id": "sleep",
	 			  "questions": [{"q_id": "sleep_hours",
	       						 "question": "how many hours have you slept yesterday?",
		       				     "choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
		    					{"q_id": "sleep_quality",
		       					 "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
		       					  "choices": [1,2,3,4,5] }  
		       					]
					}

bot = Sleek(confs, None)
bot.load_users(dummy_user_list)

def reset_DB():
	b = Backend(confs, init=True)
	b.create_survey(sleep_survey)

# TEST Survey
def test_survey_put_answers():	
	survey = Survey(sleep_survey, user_id, bot)
	assert not survey.is_complete()
	#put incorrect answer (too few)
	with pytest.raises(RuntimeError):
		survey.put_answers(["a"])
	with pytest.raises(RuntimeError):
		survey.put_answers([])
	#put incorrect answer (too many)
	with pytest.raises(RuntimeError):
		survey.put_answers(["a","b","a"])
	#put incorrect answer (invalid response)
	with pytest.raises(RuntimeError):
		survey.put_answers(["a","z"])
	with pytest.raises(RuntimeError):
		survey.put_answers(["a",1])
	with pytest.raises(RuntimeError):
		survey.put_answers(["",None])
	#good answer
	survey.put_answers(["a","b"])
	assert survey.is_complete()

def test_survey_put_answer():	
	survey = Survey(sleep_survey, user_id, bot)
	assert not survey.is_complete()	
	#put invalid response
	with pytest.raises(RuntimeError):
		survey.put_answer("a",1)
	with pytest.raises(RuntimeError):		
		survey.put_answer("",1)
	with pytest.raises(RuntimeError):
		survey.put_answer("sleep_hours","z")		
	with pytest.raises(RuntimeError):
		survey.put_answer("sleep_hours",None)	
	with pytest.raises(RuntimeError):
		survey.put_answer("sleep_hours","")	
	with pytest.raises(RuntimeError):
		survey.put_answer("sleep_hours",-1)	
	#good answer
	survey.put_answer("sleep_hours",1)	
	survey.put_answer("sleep_quality",1)	
	assert survey.is_complete()

def test_survey_put_notes():	
	survey = Survey(sleep_survey, user_id, bot)
	assert not survey.is_complete()	
	assert not survey.has_open_notes()	
	survey.put_notes(u"this is a test note")
	survey.put_notes(u"isto é um ùber test com acentuação")
	assert survey.has_open_notes()	

def survey_get_answers():
	pass

def test_survey_save():
	reset_DB()	
	data = bot.backend.get_report(user_id, survey_id)
	assert data == []
	survey = Survey(sleep_survey, user_id, bot)
	survey.put_answers(["a","b"])		
	survey.save()
	#check if data was saved
	data = bot.backend.get_report(user_id, survey_id)[0]	
	assert data[1] == user_id, set_trace()
	assert data[3] == '0' #corresponds to the first answer
	assert data[4] == '1' #corresponds to the second answer
	assert data[5] == None #corresponds to the notes
	
	#A survey with notes
	survey_2 = Survey(sleep_survey, user_id, bot)
	survey_2.put_answers(["c","d"])	
	survey_2.put_notes(u"this is a note")	
	survey_2.save()
	#check if data was saved
	data_2 = bot.backend.get_report(user_id, survey_id)[1]	
	assert data_2[1] == user_id, set_trace()
	assert data_2[3] == '2' #corresponds to the first answer
	assert data_2[4] == '3' #corresponds to the second answer
	assert data_2[5] == u"this is a note" #corresponds to the notes

	#A survey with unicode notes
	survey_3 = Survey(sleep_survey, user_id, bot)
	survey_3.put_answers(["c","d"])	
	survey_3.put_notes(u"don’t look at this wáilde nõte")	
	survey_3.save()
	#check if data was saved
	data_3 = bot.backend.get_report(user_id, survey_id)[2]	
	assert data_3[1] == user_id, set_trace()
	assert data_3[3] == '2' #corresponds to the first answer
	assert data_3[4] == '3' #corresponds to the second answer
	assert data_3[5] == u"don’t look at this wáilde nõte" #corresponds to the notes
	

def survey_get_SleekMsg():
	pass

# TEST User
def user_delete_answers():
	pass

def user_join_survey():
	pass

def user_leave_survey():
	pass

def user_reminder_save():
	pass

# TEST Sleek

def sleek_load_users():
	pass

def test_sleek_cmd_answers_report():
	reset_DB()	
	bot.users[user_id].survey_join(survey_id)
	survey = Survey(sleep_survey, user_id, bot)
	survey.put_answers(["c","d"])	
	a_note  = u"don’t look at this wáilde nõte"
	survey.put_notes(a_note)	
	survey.save()
	tokens = ["report","sleep"]
	context = {"user_id":user_id}
	out = bot.cmd_answers_report(tokens, context)
	print str(out[0])
	print str(out[1])
	assert a_note in unicode(out[1])

	# data = bot.backend.get_report(user_id, survey_id)	
	# report = sleek.format_report(sleep_survey, data)
	# #build fancy message
	# m = SleekMsg(report, msg_type="report")
	# m.set_field("survey", sleep_survey)
	# m.set_field("data", data)

def sleek_cmd_answers_delete():
	pass

def sleek_cmd_survey_join():
	pass

def sleek_cmd_survey_leave():
	pass

	
def sleek_cmd_survey_list():
	pass

	
def sleek_cmd_survey_take():
	pass

	
def sleek_cmd_reminder_add():
	pass

def sleek_run_survey():
	pass

if __name__ == "__main__":
	reset_DB()	
	bot.users[user_id].survey_join(survey_id)
	survey = Survey(sleep_survey, user_id, bot)
	survey.put_answers(["c","d"])	
	survey.put_notes(u"don’t look at this wáilde nõte")	
	survey.save()
	tokens = ["report","sleep"]
	context = {"user_id":user_id}
	out = bot.cmd_answers_report(tokens, context)
	print str(out[0])
	print str(out[1])	