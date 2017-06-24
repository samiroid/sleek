import os
import pytest
import sqlite_backend as backend
import sqlite3
import sleek

DB_path="DATA/test.db"

try:
	os.remove(DB_path)
except OSError:
	pass

bot_name="sleek"
api_token = os.environ.get('SLACK_BOT_TOKEN')

def test_chatBot():
	print "hello"
	cfg={ 
		  "greet": ["ciao","oi","holla :)"],
		  "announce": "This is a test chat bot",
		  "nack": ["q?!", "no lo se","!?"],
	      "ack": ["roger","okidoki"],
		  "help": "Please some help!"	
		}
	#create Sleek instance with default config
	bot = sleek.Sleek(api_token,"bogus", DB_path)
	assert bot.greet() in sleek.default_bot_cfg["greet"]
	assert bot.ack() in sleek.default_bot_cfg["ack"]
	assert bot.nack() in sleek.default_bot_cfg["nack"]
	assert bot.announce() == sleek.default_bot_cfg["announce"]
	assert bot.help() == sleek.default_bot_cfg["help"]

	#create Sleek instance with custom config
	bot2 = sleek.Sleek(api_token, bot_name, DB_path, cfg=cfg)
	assert bot2.greet() in cfg["greet"]
	assert bot2.ack() in cfg["ack"]
	assert bot2.nack() in cfg["nack"]
	assert bot2.help() in cfg["help"]
	assert bot2.announce() in cfg["announce"]
	os.remove(DB_path)

def test_elicit():
	assert True == False
	
def test_get_response():
	assert True == False

def test_show_report():
	assert True == False	

def test_show_survey():
	assert True == False	



# def test_join():	
# 	bot = sleek.Sleek(api_token,"bogus", DB_path)
# 	#check that user does not exist yet
# 	u = backend.load_user(DB_path, "user_id_1")
# 	assert u is None	
# 	#add user and check that it was created
# 	bot.user_join("user_id_1", "survey_id_1")	
# 	u2 = backend.load_user(DB_path, "user_id_1")
# 	assert u2[backend.USER_ID] == "user_id_1"
# 	os.remove(DB_path)

# def test_leave():
# 	bot = sleek.Sleek(api_token,"bogus", DB_path)
# 	#check that user does not exist yet
# 	u = backend.load_user(DB_path, "user_id_1")
# 	assert u is None	
# 	#add user and check that it was created
# 	bot.user_join("survey_1", "user_id_1", "username_1")	
# 	u2 = backend.load_user(DB_path, "user_id_1")
# 	assert u2[backend.USER_ID] == "user_id_1"
# 	bot.leave("survey_1", "user_id_1")
# 	#check that user does not exist anymore
# 	u3 = backend.load_user(DB_path, "user_id_1")
# 	assert u3 is None	
# 	os.remove(DB_path)

# def test_update():
# 	bot = sleek.Sleek(api_token,"bogus", DB_path)	
# 	#add user and check that it was created
# 	bot.user_join("survey_1", "user_id_1", "username_1")	
# 	u2 = backend.load_user(DB_path, "user_id_1")
# 	assert u2[backend.USER_ID] == "user_id_1"
# 	assert u2[backend.AM_CHECK] is None
# 	assert u2[backend.PM_CHECK] is None
# 	nu_confs = {"new_am_check":10, "new_pm_check":11}
# 	bot.update("user_id_1", nu_confs)
# 	#check that user does not exist anymore
# 	u2 = backend.load_user(DB_path, "user_id_1")
# 	assert u2[backend.USER_ID] == "user_id_1"
# 	assert u2[backend.AM_CHECK] is nu_confs["new_am_check"]
# 	assert u2[backend.PM_CHECK] is nu_confs["new_pm_check"]
# 	os.remove(DB_path)

# def test_save_survey():
# 	bot = sleek.Sleek(api_token,"bogus", DB_path)	
# 	#add user to survey
# 	bot.user_join("survey_1", "user_id_1", "username_1")		
# 	with pytest.raises(NotImplementedError):
# 		bot.save_survey("user_id", "survey_1")

# 	os.remove(DB_path)

# def test_get_survey():
# 	raise NotImplementedError


