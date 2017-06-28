"""
	Methods to comunicate with a backend
"""

import json
import os
import sqlite3
#from ipdb import set_trace

#user table columns
USER_ID = 0
USER_ACTIVE = 1

#user_surveys table columns
SURVEYS_USER_ID = 0
SURVEYS_ID = 1
SURVEYS_AM_CHECK = 2
SURVEYS_PM_CHECK = 3
SURVEYS_ACTIVE = 4

def init(DB_path):
	"""
		Create database with tables 'users' and 'surveys' and 'user_surveys'
	"""
	USERS =        ''' CREATE TABLE users(id TEXT PRIMARY KEY, 
										  active INTEGER DEFAULT 1) '''
	
	USER_SURVEYS = ''' CREATE TABLE user_surveys(user_id TEXT, survey_id TEXT, 
										         am_check TEXT, pm_check TEXT, active INTEGER DEFAULT 1, 
										         PRIMARY KEY(user_id, survey_id))  '''

	SURVEYS = ''' CREATE TABLE surveys(id TEXT PRIMARY KEY, survey TEXT)  '''

	try:
		#try to remove the file
		os.remove(DB_path)
	except:
		pass
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	#create users table
	cursor.execute(''' DROP TABLE IF EXISTS users; ''')	
	cursor.execute(USERS)	
	#create user_surveys table
	cursor.execute(''' DROP TABLE IF EXISTS user_surveys; ''')
	cursor.execute(USER_SURVEYS)
	#create surveys table
	cursor.execute(''' DROP TABLE IF EXISTS surveys; ''')
	cursor.execute(SURVEYS)
	db.commit()
	db.close()		

def __create_table(DB_path, table_name, fields, override=False):	
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	if override:
		 drop = ''' DROP TABLE IF EXISTS {} '''.format(table_name)
		 cursor.execute(drop)	
	sql_fields = 'ID INTEGER PRIMARY KEY AUTOINCREMENT, ' + ' TEXT, '.join(fields) + ' TEXT' + ', COMPLETE INTEGER DEFAULT 0'
 	create = ''' CREATE TABLE {}({}) '''.format(table_name, sql_fields)
	#create table		
	cursor.execute(create)	
	db.commit()
	db.close()

def __get(DB_path, sql, params=None):
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	if params is not None:
		cursor.execute(sql, tuple(params))
	else:
		cursor.execute(sql)
	res = cursor.fetchall()	
	db.close()	
	return res

def __update(DB_path, sql, params):
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()		
	cursor.execute(sql, params)
	rc = cursor.rowcount
	db.commit()
	db.close()
	return rc

def __put(DB_path, table_name, row):
	"""
		row is a dictionary: {column: value}
	"""
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()		
	keys = row.keys()
	values = row.values()
	sql_keys = ','.join(keys)
	sql_values =  ('?,'*len(values)).strip(',')
	sql_insert = ''' INSERT INTO {}({}) VALUES({}) '''.format(table_name,sql_keys,sql_values)
	cursor.execute(sql_insert, values)		
	rowid = cursor.lastrowid
	db.commit()
	db.close()
	return rowid

def __table_exists(DB_path, table_name):
	"""
		Auxiliary method to check if a table exists
	"""	
	check_table_sql = ''' SELECT count(*) FROM sqlite_master WHERE type='table' AND name=? '''
	t = __get(DB_path, check_table_sql,(table_name,))[0][0]
	return t == 1

def add_user(DB_path, user_id):
	row = {"id":user_id}
	__put(DB_path, "users", row) > 0

def create_survey(DB_path, survey):
	table_name = "survey_"+survey["survey_id"]	
	fields = ["user_id","timestamp"] + [q["id"] for q in survey["survey"] ]	
	try:
		__put(DB_path, "surveys", {"id":survey["survey_id"],"survey":json.dumps(survey)})
	except sqlite3.IntegrityError: 
		raise RuntimeError("survey already exists")
	__create_table(DB_path, table_name, fields)

def delete_responses(DB_path, user_id, survey_id):
	sql = '''DELETE FROM survey_{} WHERE user_id=?'''.format(survey_id)
	return __update(DB_path, sql, (user_id,)) > 0

def delete_survey(DB_path, survey_id):
	sql = '''DELETE FROM surveys WHERE id=?'''
	return  __update(DB_path, sql, (survey_id,)) > 0	

def get_user(DB_path, user_id):
	sql = '''SELECT * FROM users WHERE id=?'''	
	x = __get(DB_path, sql,(user_id,))
	if len(x) > 0:
		return x[0]
	return None

def get_users(DB_path):
	sql = '''SELECT * FROM users'''	
	return __get(DB_path, sql)

def get_report(DB_path, user_id, survey_id):
	survey_table = "survey_{}".format(survey_id)
	if not __table_exists(DB_path, survey_table):
		raise RuntimeError("survey does not exist")
	sql = '''SELECT * FROM {} WHERE user_id=? AND complete=1 order by timestamp DESC'''.format(survey_table)
	return __get(DB_path, sql,(user_id,))

def get_response(DB_path, user_id, survey_id, response_id):
	sql = '''SELECT * FROM survey_{} WHERE user_id=? AND id=?'''.format(survey_id)	
	resp = __get(DB_path, sql,(user_id,response_id,))
	if len(resp) > 0:
		return resp[0]
	else:
		return resp

def get_survey(DB_path, survey_id):
	sql = '''SELECT survey FROM surveys WHERE id=? '''
	x = __get(DB_path, sql,(survey_id,))
	if len(x) > 0:
		return json.loads(x[0][0])
	return None

def join_survey(DB_path, user_id, survey_id, am_check=9, pm_check=4):	
	if not __table_exists(DB_path, "survey_"+survey_id):
		raise RuntimeError("survey {} not found".format(survey_id))
	if get_user(DB_path, user_id) is None:
		add_user(DB_path, user_id)	
	row = {"user_id":user_id, "survey_id":survey_id, "am_check":am_check, "pm_check":pm_check}
	try:		
		return __put(DB_path, "user_surveys", row) > 0
	except sqlite3.IntegrityError:				
		raise RuntimeError("user {} already joined survey {}".format(user_id, survey_id))

def list_surveys(DB_path,user_id=None):	
	if user_id is None:
		sql = ''' SELECT * FROM surveys'''
		return __get(DB_path, sql)
	else:
		sql = ''' SELECT * FROM user_surveys WHERE user_id=? AND active=1'''
		return __get(DB_path, sql,(user_id,))

def new_response(DB_path, user_id, survey_id, timestamp):
	return __put(DB_path, "survey_"+survey_id, {"user_id":user_id, "timestamp":timestamp}) 

def schedule_survey(DB_path, user_id, survey_id, am_check, pm_check):
	sql = '''UPDATE user_surveys SET am_check=?, pm_check=? WHERE user_id=? AND survey_id=?'''
	return __update(DB_path, sql, (am_check, pm_check, user_id, survey_id))	

def toggle_user(DB_path, user_id, active=True):
	sql = '''UPDATE users SET active=? WHERE id=?'''
	return __update(DB_path, sql, (active, user_id)) > 0	

def toggle_survey(DB_path, user_id, survey_id, active=True):
	sql = '''UPDATE user_surveys SET active=? WHERE user_id=? AND survey_id=?'''
	return __update(DB_path, sql, (active, user_id, survey_id)) > 0

def close_response(DB_path, user_id, survey_id, response_id):
	sql = '''UPDATE survey_{} SET complete=1 WHERE user_id=? AND id=? '''.format(survey_id)
	return __update(DB_path, sql, (user_id, response_id)) > 0

def save_response(DB_path, survey_id, user_id, response_id, update):
	"""
		row is a dictionary: {column: value}
	"""
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()		
	fields = update.keys()
	values = update.values()
	update_fields = ','.join([k+"=?" for k in fields]).strip(',')	
	sql_insert = ''' UPDATE survey_{} SET {} WHERE user_id=? and id=? '''.format(survey_id,update_fields)
	cursor.execute(sql_insert, values+[user_id,response_id])		
	db.commit()
	db.close()
