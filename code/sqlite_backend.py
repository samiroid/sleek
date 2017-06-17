"""
	Methods to comunicate with a backend
"""

import sqlite3
#from ipdb import set_trace
#user table columns
USER_ID = 0
USER_NAME = 1
AM_CHECK = 2
PM_CHECK = 3
#reports table columns
REP_DAY = 1
REP_PERIOD = 2
REP_SLEEP_HOURS = 3
REP_SLEEP_QUALITY = 4
REP_STRESS = 5

def create_DB(DB_path):
	sql_users = ''' CREATE TABLE users(user_id TEXT PRIMARY KEY, username TEXT, 
									   am_check INTEGER, pm_check INTEGER) '''
	sql_reports = ''' CREATE TABLE reports(user_id TEXT, day TEXT, 
										   period TEXT, sleep_hours INTEGER, 
										   sleep_quality INTEGER, stress INTEGER,
										   PRIMARY KEY (user_id, day, period),
										   FOREIGN KEY (user_id) REFERENCES users(user_id)) '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	#create users table
	cursor.execute('''DROP TABLE IF EXISTS users''')
	cursor.execute(sql_users)
	db.commit()
	#create reports table
	cursor.execute('''DROP TABLE IF EXISTS reports''')
	cursor.execute(sql_reports)
	db.commit()
	db.close()	

def add_user(DB_path, user_id, username, am_check=None, pm_check=None):
	sql = '''INSERT INTO users(user_id, username, am_check, pm_check) VALUES(?,?,?,?)'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id,username, am_check, pm_check))
	db.commit()
	db.close()	

def load_user(DB_path, user_id):
	sql = '''SELECT * FROM users WHERE user_id=?'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id,))
	user = cursor.fetchone()	
	db.close()	
	return user

def load_users(DB_path):
	sql = '''SELECT * FROM users'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql)
	users = cursor.fetchall()
	db.close()	
	return users

def load_report(DB_path, user_id, day, period):
	sql = '''SELECT * FROM reports WHERE user_id=? AND day=? AND period=?'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id, day, period,))
	rep = cursor.fetchone()	
	db.close()	
	return rep

def update_user(DB_path, user_id, new_username=None, new_am_check=None, new_pm_check=None):
	sql = '''UPDATE users SET username=?, am_check=?, pm_check=? WHERE user_id=?'''
	#load current values
	user = load_user(DB_path, user_id)
	if new_username is not None:
		username=new_username
	else:
		username=user[USER_NAME]

	if new_am_check is not None:
		am_check=new_am_check
	else:
		am_check=user[AM_CHECK]
	
	if new_pm_check is not None:
		pm_check=new_pm_check
	else:
		pm_check=user[PM_CHECK]
	#update user	
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	cursor.execute(sql, (username,am_check,pm_check,user_id,))	
	db.commit()
	db.close()	

def remove_user(DB_path, user_id):
	sql = '''DELETE FROM users WHERE user_id=?'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id,))
	db.commit()
	db.close()

def add_report(DB_path, user_id, day, period, sleep_hours=None, sleep_quality=None, stress=None):
	assert period is not None and period.upper() in ["AM","PM"]
	if sleep_hours is not None:
		assert type(sleep_hours) == int and \
			   sleep_hours >= 0 and \
			   sleep_hours < 24
	
	if sleep_quality is not None:		
		assert type(sleep_quality) == int and \
			   sleep_quality >= 1 and \
			   sleep_quality <= 5
	if stress is not None:
		assert type(stress) == int and \
	    	   stress >= 1 and \
	           stress <= 5 

	sql = '''INSERT INTO reports(user_id, day, period, sleep_hours, sleep_quality, stress) 
				    VALUES(?,?,?,?,?,?)'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id, day, period, sleep_hours, sleep_quality, stress,))
	db.commit()
	db.close()

def update_report(DB_path, user_id, day, period, sleep_hours=None, sleep_quality=None, stress=None):
	assert period.upper() in ["AM","PM"]
	sql = '''UPDATE reports SET {}
			 WHERE user_id=? AND day=? AND period=?'''
	valz=[]
	fields=""
	if sleep_hours is not None:
		assert type(sleep_hours) == int and sleep_hours and sleep_hours >= 0 and sleep_hours < 24
		fields+="sleep_hours=?," 
		valz+=[sleep_hours]	
	
	if sleep_quality is not None:
		assert type(sleep_quality) == int and sleep_quality >= 1 and sleep_quality <= 5
		fields+="sleep_quality=?," 
		valz+=[sleep_quality]
	
	if stress is not None:
		assert type(stress) == int and stress >= 1 and stress <= 5
		fields+="stress=?," 
		valz+=[stress]
	
	assert len(valz)>0	
	valz+=[user_id, day, period]
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	stmt = sql.format(fields.rstrip(","))	
	cursor.execute(stmt, tuple(valz))
	db.commit()
	db.close()
