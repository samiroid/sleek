import os
import pytest
import sqlite_backend as backend
import sqlite3

test_DB="DATA/test.db"

try:
	os.remove(test_DB)
except OSError:
	pass

def test_createDB():	
	backend.create_DB(test_DB)
	assert os.path.isfile(test_DB), "file was not created"
	os.remove(test_DB)

def test_add_user():
	#create DB
	backend.create_DB(test_DB)
	#create user with default check times
	user_1="alice"
	id_1="123"
	backend.add_user(test_DB, id_1, user_1)
	#create user with specific check times
	user_2="bob"
	id_2="456"
	am_check = 9 #dt.time(9,0,0)
	pm_check = 5 #dt.time(17,0,0)	
	backend.add_user(test_DB, id_2, user_2, am_check, pm_check)	
	#check that user_1 was correctly created
	db = sqlite3.connect(test_DB)
	cursor = db.cursor()
	sql = '''SELECT * FROM users WHERE user_id=?'''
	cursor.execute(sql, (id_1,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == id_1 and \
		   resp[backend.USER_NAME] == user_1
	#check that user_2 was correctly created
	cursor.execute(sql, (id_2,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]  == id_2 and \
	       resp[backend.AM_CHECK] == am_check and \
	       resp[backend.PM_CHECK] == pm_check and \
	       resp[backend.USER_NAME] == user_2 
	#remove test DB
	os.remove(test_DB)

def test_load_user():
	#create DB
	backend.create_DB(test_DB)
	#create user 
	username="alice"
	user_id="123"
	backend.add_user(test_DB, user_id, username)			
	#check that user was correctly created
	db = sqlite3.connect(test_DB)
	cursor = db.cursor()
	sql = '''SELECT * FROM users WHERE user_id=?'''
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == user_id and \
		   resp[backend.USER_NAME] == username
	#load user
	user = backend.load_user(test_DB, user_id)
	assert user[backend.USER_ID]   == user_id and \
		   user[backend.USER_NAME] == username
	#remove test DB
	os.remove(test_DB)

def test_remove_user():	
	#create DB
	backend.create_DB(test_DB)
	#create user 
	username="alice"
	user_id="123"
	backend.add_user(test_DB, user_id, username)			
	#check that user was correctly created
	db = sqlite3.connect(test_DB)
	cursor = db.cursor()
	sql = '''SELECT * FROM users WHERE user_id=?'''
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == user_id and \
		   resp[backend.USER_NAME] == username
	#remove user
	backend.remove_user(test_DB, user_id)
	#check user does not exist
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp is None	
	#remove test DB
	os.remove(test_DB)

def test_update_user():
	"""
		assumes add_user() and load_user() are correct
	"""
	#create DB
	backend.create_DB(test_DB)
	#create user 
	username="alice"
	user_id="123"
	am_check=1
	pm_check=2
	backend.add_user(test_DB, user_id, username, am_check, pm_check)			
	user = backend.load_user(test_DB, user_id)
	#check initial values
	assert user[backend.USER_NAME] == username and \
		   user[backend.AM_CHECK]  == am_check and \
		   user[backend.PM_CHECK]  == pm_check
	
	#update username
	nu_username="bob"
	backend.update_user(test_DB, user_id,new_username=nu_username)
	user = backend.load_user(test_DB, user_id)	
	assert user[backend.USER_NAME] == nu_username 		   
	
	#update am_check
	nu_am_check=10
	backend.update_user(test_DB, user_id,new_am_check=nu_am_check)
	user = backend.load_user(test_DB, user_id)
	assert user[backend.AM_CHECK]  == nu_am_check 
	
	#update pm_check
	nu_pm_check=8
	backend.update_user(test_DB, user_id,new_pm_check=nu_pm_check)
	user = backend.load_user(test_DB, user_id)
	assert user[backend.PM_CHECK]  == nu_pm_check
	
	#update all	
	#create a new user
	another_username="carl"
	another_user_id="456"
	another_am_check=9
	another_pm_check=6
	backend.add_user(test_DB, another_user_id, another_username, 
					 another_am_check, another_pm_check)			
	user = backend.load_user(test_DB, user_id)
	#update all the fields
	backend.update_user(test_DB, another_user_id, new_username=username,
							   new_am_check=am_check, new_pm_check=pm_check)
	user = backend.load_user(test_DB, another_user_id)
	assert user[backend.USER_NAME] == username and \
		   user[backend.AM_CHECK]  == am_check and \
		   user[backend.PM_CHECK]  == pm_check
	
	#remove test DB
	os.remove(test_DB)

def test_add_report():	
	"""
		assumes add_user() is correct
	"""
	sql = '''SELECT * FROM reports WHERE user_id=? AND day=? AND period=?'''
	#create DB
	backend.create_DB(test_DB)
	#create user 
	username="alice"
	user_id="123"
	backend.add_user(test_DB, user_id, username)
	#create report
	day=1
	period="AM"
	sleep_hours=8
	sleep_quality=5
	stress=1	
	db = sqlite3.connect(test_DB)	
	cursor = db.cursor()	
	#check that the report does not exist
	cursor.execute(sql, (user_id,day,period))
	resp = cursor.fetchone()
	assert resp is None	
	#insert report with all the fields
	backend.add_report(test_DB, user_id, str(day), period, sleep_hours, sleep_quality, stress)	
	#check that report was inserted	
	cursor.execute(sql, (user_id,day,period))
	resp = cursor.fetchone()	
	assert resp[backend.REP_STRESS] == stress and \
		   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
		   resp[backend.REP_SLEEP_QUALITY] == sleep_quality	

	#insert report with only sleep hours
	day+=1 #avoid PK violation
	backend.add_report(test_DB, user_id, str(day), period, sleep_hours=sleep_hours)	
	#check that report was inserted	
	cursor.execute(sql, (user_id,day,period))
	resp = cursor.fetchone()	
	assert resp[backend.REP_STRESS] == None and \
		   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
		   resp[backend.REP_SLEEP_QUALITY] == None	

   	#insert report with only sleep quality
	day+=1 #avoid PK violation
	backend.add_report(test_DB, user_id, str(day), period, sleep_quality=sleep_quality)	
	#check that report was inserted	
	cursor.execute(sql, (user_id,day,period))
	resp = cursor.fetchone()	
	assert resp[backend.REP_STRESS] == None and \
		   resp[backend.REP_SLEEP_HOURS] == None and \
		   resp[backend.REP_SLEEP_QUALITY] == sleep_quality	

	#insert report with only stress
	day+=1 #avoid PK violation
	backend.add_report(test_DB, user_id, str(day), period, stress=stress)	
	#check that report was inserted	
	cursor.execute(sql, (user_id,day,period))
	resp = cursor.fetchone()	
	assert resp[backend.REP_STRESS] == stress and \
		   resp[backend.REP_SLEEP_HOURS] == None and \
		   resp[backend.REP_SLEEP_QUALITY] == None

	#remove test DB
	os.remove(test_DB)

def test_add_report_values():	
	"""
		assumes add_user() is correct
	"""	
	#create DB
	backend.create_DB(test_DB)
	#create user 
	username="alice"
	user_id="123"
	backend.add_user(test_DB, user_id, username)
	#create report
	day=1
	period="AM"
	sleep_hours=8
	sleep_quality=5
	stress=1	

	#check period
	#invalid
	for p in ["AMA","dasPM","",None]:
		with pytest.raises(AssertionError):
			backend.add_report(test_DB, user_id, str(day), p, sleep_hours, sleep_quality, stress)

	#valid
	for p in ["AM","PM"]:
		day+=1
		backend.add_report(test_DB, user_id, str(day), p, sleep_hours, sleep_quality, stress)			
		#check that report was inserted	
		resp = backend.load_report(test_DB, user_id, str(day), p)
		assert resp[backend.REP_STRESS] == stress and \
			   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
			   resp[backend.REP_SLEEP_QUALITY] == sleep_quality

    #check sleep hours
	#invalid
	for sh in [-1,"",26,24]:
		print sh
		with pytest.raises(AssertionError):
			backend.add_report(test_DB, user_id, day, period, sh, sleep_quality, stress)
	#valid
	for sh in [1,23,8,None]:
		day+=1
		backend.add_report(test_DB, user_id, str(day), period, sh, sleep_quality, stress)			
		#check that report was inserted	
		resp = backend.load_report(test_DB, user_id, day, period)
		assert resp[backend.REP_STRESS] == stress and \
			   resp[backend.REP_SLEEP_HOURS] == sh and \
			   resp[backend.REP_SLEEP_QUALITY] == sleep_quality
	
    #check sleep quality
	#invalid
	for sq in [0, -1,"",26,24,6]:
		with pytest.raises(AssertionError):
			backend.add_report(test_DB, user_id, day, period, sleep_hours, sq, stress)
	#valid
	for sq in [1,5,3,None]:
		day+=1
		backend.add_report(test_DB, user_id, day, period, sleep_hours, sq, stress)				
		#check that report was inserted	
		resp = backend.load_report(test_DB, user_id, day, period)
		assert resp[backend.REP_STRESS] == stress and \
			   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
			   resp[backend.REP_SLEEP_QUALITY] == sq

	#check stress
	#invalid
	for st in [0,-1,"",26,24,6]:
		with pytest.raises(AssertionError):
			backend.add_report(test_DB, user_id, day, period, sleep_hours, sleep_quality, st)
	# #valid
	for st in [1,5,3,None]:
		day+=1
		backend.add_report(test_DB, user_id, day, period, sleep_hours, sleep_quality, st)				
		#check that report was inserted	
		resp = backend.load_report(test_DB, user_id, day, period)
		assert resp[backend.REP_STRESS] == st and \
			   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
			   resp[backend.REP_SLEEP_QUALITY] == sleep_quality

	#remove test DB
	os.remove(test_DB)

def test_update_report():	
	"""
		assumes add_user() is correct
	"""
	sql = '''SELECT * FROM reports WHERE user_id=? AND day=? AND period=?'''
	#create DB
	backend.create_DB(test_DB)
	#create user 
	username="alice"
	user_id="123"
	backend.add_user(test_DB, user_id, username)
	#create report
	day="1"
	period="AM"
	sleep_hours=8
	sleep_quality=5
	stress=1	
	db = sqlite3.connect(test_DB)	
	cursor = db.cursor()	
	#check that the report does not exist
	cursor.execute(sql, (user_id,day,period))
	resp = cursor.fetchone()
	assert resp is None	
	#insert report
	backend.add_report(test_DB, user_id, day, period, stress=stress)	
	#check that report was inserted		
	resp = backend.load_report(test_DB, user_id, day, period)
	assert resp[backend.REP_STRESS] == stress and \
		   resp[backend.REP_SLEEP_HOURS] == None and \
		   resp[backend.REP_SLEEP_QUALITY] == None
	#update report with sleep hours
	backend.update_report(test_DB, user_id, day, period,sleep_hours=sleep_hours)
	#check that report was updated		
	resp = backend.load_report(test_DB, user_id, day, period)
	assert resp[backend.REP_STRESS] == stress and \
		   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
		   resp[backend.REP_SLEEP_QUALITY] == None
	#update report with sleep quality
	backend.update_report(test_DB, user_id, day, period,sleep_quality=sleep_quality)
	#check that report was updated		
	resp = backend.load_report(test_DB, user_id, day, period)
	assert resp[backend.REP_STRESS] == stress and \
		   resp[backend.REP_SLEEP_HOURS] == sleep_hours and \
		   resp[backend.REP_SLEEP_QUALITY] == sleep_quality
	#remove test DB
	os.remove(test_DB)


