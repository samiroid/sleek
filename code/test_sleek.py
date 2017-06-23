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

def test_configs():
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

def test_join():	
	bot = sleek.Sleek(api_token,"bogus", DB_path)
	#check that user does not exist yet
	u = backend.load_user(DB_path, "user_id_1")
	assert u is None	
	#add user and check that it was created
	bot.user_join("user_id_1", "survey_id_1")	
	u2 = backend.load_user(DB_path, "user_id_1")
	assert u2[backend.USER_ID] == "user_id_1"
	os.remove(DB_path)

def test_leave():
	bot = sleek.Sleek(api_token,"bogus", DB_path)
	#check that user does not exist yet
	u = backend.load_user(DB_path, "user_id_1")
	assert u is None	
	#add user and check that it was created
	bot.user_join("survey_1", "user_id_1", "username_1")	
	u2 = backend.load_user(DB_path, "user_id_1")
	assert u2[backend.USER_ID] == "user_id_1"
	bot.leave("survey_1", "user_id_1")
	#check that user does not exist anymore
	u3 = backend.load_user(DB_path, "user_id_1")
	assert u3 is None	
	os.remove(DB_path)

def test_update():
	bot = sleek.Sleek(api_token,"bogus", DB_path)	
	#add user and check that it was created
	bot.user_join("survey_1", "user_id_1", "username_1")	
	u2 = backend.load_user(DB_path, "user_id_1")
	assert u2[backend.USER_ID] == "user_id_1"
	assert u2[backend.AM_CHECK] is None
	assert u2[backend.PM_CHECK] is None
	nu_confs = {"new_am_check":10, "new_pm_check":11}
	bot.update("user_id_1", nu_confs)
	#check that user does not exist anymore
	u2 = backend.load_user(DB_path, "user_id_1")
	assert u2[backend.USER_ID] == "user_id_1"
	assert u2[backend.AM_CHECK] is nu_confs["new_am_check"]
	assert u2[backend.PM_CHECK] is nu_confs["new_pm_check"]
	os.remove(DB_path)

def test_save_survey():
	bot = sleek.Sleek(api_token,"bogus", DB_path)	
	#add user to survey
	bot.user_join("survey_1", "user_id_1", "username_1")		
	with pytest.raises(NotImplementedError):
		bot.save_survey("user_id", "survey_1")

	os.remove(DB_path)

def test_get_survey():
	raise NotImplementedError


# def test_add_report():	
# 	"""
# 		assumes add_user() is correct
# 	"""
# 	sql = '''SELECT * FROM reports WHERE user_id=? AND day=? AND period=?'''
# 	#create DB
# 	backend.create_DB(test_DB)
# 	#create user 
# 	username="alice"
# 	user_id="123"
# 	backend.add_user(test_DB, user_id, username)
# 	#create report
# 	day=1
# 	period="AM"
# 	sleep_hours=8
# 	sleep_quality=5
# 	stress=1	
# 	db = sqlite3.connect(test_DB)	
# 	cursor = db.cursor()	
# 	#check that the report does not exist
# 	cursor.execute(sql, (user_id,day,period))
# 	resp = cursor.fetchone()
# 	assert resp is None	
# 	#insert report with all the fields
# 	backend.add_report(test_DB, user_id, str(day), period, sleep_hours, sleep_quality, stress)	
# 	#check that report was inserted	
# 	cursor.execute(sql, (user_id,day,period))
# 	resp = cursor.fetchone()	
# 	assert resp[backend.REP_STRESS] == stress and \
# 		   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
# 		   resp[backend.REP_SLEEP_QUALITY] == sleep_quality	

# 	#insert report with only sleep hours
# 	day+=1 #avoid PK violation
# 	backend.add_report(test_DB, user_id, str(day), period, sleep_hours=sleep_hours)	
# 	#check that report was inserted	
# 	cursor.execute(sql, (user_id,day,period))
# 	resp = cursor.fetchone()	
# 	assert resp[backend.REP_STRESS] == None and \
# 		   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
# 		   resp[backend.REP_SLEEP_QUALITY] == None	

#    	#insert report with only sleep quality
# 	day+=1 #avoid PK violation
# 	backend.add_report(test_DB, user_id, str(day), period, sleep_quality=sleep_quality)	
# 	#check that report was inserted	
# 	cursor.execute(sql, (user_id,day,period))
# 	resp = cursor.fetchone()	
# 	assert resp[backend.REP_STRESS] == None and \
# 		   resp[backend.REP_SLEEP_HOURS] == None and \
# 		   resp[backend.REP_SLEEP_QUALITY] == sleep_quality	

# 	#insert report with only stress
# 	day+=1 #avoid PK violation
# 	backend.add_report(test_DB, user_id, str(day), period, stress=stress)	
# 	#check that report was inserted	
# 	cursor.execute(sql, (user_id,day,period))
# 	resp = cursor.fetchone()	
# 	assert resp[backend.REP_STRESS] == stress and \
# 		   resp[backend.REP_SLEEP_HOURS] == None and \
# 		   resp[backend.REP_SLEEP_QUALITY] == None

# 	#remove test DB
# 	os.remove(test_DB)

# def test_add_report_values():	
# 	"""
# 		assumes add_user() is correct
# 	"""	
# 	#create DB
# 	backend.create_DB(test_DB)
# 	#create user 
# 	username="alice"
# 	user_id="123"
# 	backend.add_user(test_DB, user_id, username)
# 	#create report
# 	day=1
# 	period="AM"
# 	sleep_hours=8
# 	sleep_quality=5
# 	stress=1	

# 	#check period
# 	#invalid
# 	for p in ["AMA","dasPM","",None]:
# 		with pytest.raises(AssertionError):
# 			backend.add_report(test_DB, user_id, str(day), p, sleep_hours, sleep_quality, stress)

# 	#valid
# 	for p in ["AM","PM"]:
# 		day+=1
# 		backend.add_report(test_DB, user_id, str(day), p, sleep_hours, sleep_quality, stress)			
# 		#check that report was inserted	
# 		resp = backend.load_report(test_DB, user_id, str(day), p)
# 		assert resp[backend.REP_STRESS] == stress and \
# 			   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
# 			   resp[backend.REP_SLEEP_QUALITY] == sleep_quality

#     #check sleep hours
# 	#invalid
# 	for sh in [-1,"",26,24]:
# 		print sh
# 		with pytest.raises(AssertionError):
# 			backend.add_report(test_DB, user_id, day, period, sh, sleep_quality, stress)
# 	#valid
# 	for sh in [1,23,8,None]:
# 		day+=1
# 		backend.add_report(test_DB, user_id, str(day), period, sh, sleep_quality, stress)			
# 		#check that report was inserted	
# 		resp = backend.load_report(test_DB, user_id, day, period)
# 		assert resp[backend.REP_STRESS] == stress and \
# 			   resp[backend.REP_SLEEP_HOURS] == sh and \
# 			   resp[backend.REP_SLEEP_QUALITY] == sleep_quality
	
#     #check sleep quality
# 	#invalid
# 	for sq in [0, -1,"",26,24,6]:
# 		with pytest.raises(AssertionError):
# 			backend.add_report(test_DB, user_id, day, period, sleep_hours, sq, stress)
# 	#valid
# 	for sq in [1,5,3,None]:
# 		day+=1
# 		backend.add_report(test_DB, user_id, day, period, sleep_hours, sq, stress)				
# 		#check that report was inserted	
# 		resp = backend.load_report(test_DB, user_id, day, period)
# 		assert resp[backend.REP_STRESS] == stress and \
# 			   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
# 			   resp[backend.REP_SLEEP_QUALITY] == sq

# 	#check stress
# 	#invalid
# 	for st in [0,-1,"",26,24,6]:
# 		with pytest.raises(AssertionError):
# 			backend.add_report(test_DB, user_id, day, period, sleep_hours, sleep_quality, st)
# 	# #valid
# 	for st in [1,5,3,None]:
# 		day+=1
# 		backend.add_report(test_DB, user_id, day, period, sleep_hours, sleep_quality, st)				
# 		#check that report was inserted	
# 		resp = backend.load_report(test_DB, user_id, day, period)
# 		assert resp[backend.REP_STRESS] == st and \
# 			   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
# 			   resp[backend.REP_SLEEP_QUALITY] == sleep_quality

# 	#remove test DB
# 	os.remove(test_DB)

# def test_update_report():	
# 	"""
# 		assumes add_user() is correct
# 	"""
# 	sql = '''SELECT * FROM reports WHERE user_id=? AND day=? AND period=?'''
# 	#create DB
# 	backend.create_DB(test_DB)
# 	#create user 
# 	username="alice"
# 	user_id="123"
# 	backend.add_user(test_DB, user_id, username)
# 	#create report
# 	day="1"
# 	period="AM"
# 	sleep_hours=8
# 	sleep_quality=5
# 	stress=1	
# 	db = sqlite3.connect(test_DB)	
# 	cursor = db.cursor()	
# 	#check that the report does not exist
# 	cursor.execute(sql, (user_id,day,period))
# 	resp = cursor.fetchone()
# 	assert resp is None	
# 	#insert report
# 	backend.add_report(test_DB, user_id, day, period, stress=stress)	
# 	#check that report was inserted		
# 	resp = backend.load_report(test_DB, user_id, day, period)
# 	assert resp[backend.REP_STRESS] == stress and \
# 		   resp[backend.REP_SLEEP_HOURS] == None and \
# 		   resp[backend.REP_SLEEP_QUALITY] == None
# 	#update report with sleep hours
# 	backend.update_report(test_DB, user_id, day, period,sleep_hours=sleep_hours)
# 	#check that report was updated		
# 	resp = backend.load_report(test_DB, user_id, day, period)
# 	assert resp[backend.REP_STRESS] == stress and \
# 		   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
# 		   resp[backend.REP_SLEEP_QUALITY] == None
# 	#update report with sleep quality
# 	backend.update_report(test_DB, user_id, day, period,sleep_quality=sleep_quality)
# 	#check that report was updated		
# 	resp = backend.load_report(test_DB, user_id, day, period)
# 	assert resp[backend.REP_STRESS] == stress and \
# 		   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
# 		   resp[backend.REP_SLEEP_QUALITY] == sleep_quality
# 	#remove test DB
# 	os.remove(test_DB)


