"""
	Methods to comunicate with a backend
"""

import sqlite3
#from ipdb import set_trace

#user table columns
USER_ID = 0
USER_NAME = 1
USER_ACTIVE = 2

#user_surveys table columns
SURVEYS_USER_ID = 0
SURVEYS_ID = 1
SURVEYS_AM_CHECK = 2
SURVEYS_PM_CHECK = 3
SURVEYS_ACTIVE = 4

def __create_DB(DB_path, override=False):
	"""
		Create database with tables 'users' and 'surveys'
	"""
	USERS =        ''' CREATE TABLE users(id TEXT PRIMARY KEY, username TEXT, 
										  active INTEGER DEFAULT 1) '''
	
	USER_SURVEYS = ''' CREATE TABLE user_surveys(user_id TEXT, survey_id TEXT, 
										         am_check TEXT, pm_check TEXT, active INTEGER DEFAULT 1, 
										         PRIMARY KEY(user_id, survey_id))  '''

	SURVEYS = ''' CREATE TABLE surveys(id TEXT, survey TEXT)  '''

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
	print "[created backend @ {}]".format(DB_path)		

def __create_table(DB_path, table_name, fields, override=False):	
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	if override:
		 drop = ''' DROP TABLE IF EXISTS {} '''.format(table_name)
		 cursor.execute(drop)	
	sql_fields = ' TEXT, '.join(fields) + ' TEXT'
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
	db.commit()
	db.close()

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
	db.commit()
	db.close()

def __table_exists(DB_path, table_name):
	"""
		Auxiliary method to check if a table exists
	"""	
	check_table_sql = ''' SELECT count(*) FROM sqlite_master WHERE type='table' AND name=? '''
	t = __get(DB_path, check_table_sql,(table_name,))[0][0]
	return t == 1

def add_user(DB_path, user_id, username):
	row = {"id":user_id,"username":username}
	__put(DB_path, "users", row)

def create_survey(DB_path, survey):
	table_name = "survey_"+survey["survey_id"]	
	fields = ["user_id","timestamp"] + [q["id"] for q in survey["survey"] ]

	print "[created survey table: {} | columns: {}]".format(table_name,repr(fields))	
	__put(DB_path, "surveys", {"id":survey["survey_id"],"survey":repr(survey)})
	__create_table(DB_path, table_name, fields)

def delete_user(DB_path, user_id):
	sql = '''DELETE FROM users WHERE id=?'''
	__update(DB_path, sql, (user_id,))		

def delete_survey(DB_path, survey_id):
	sql = '''DELETE FROM surveys WHERE id=?'''
	__update(DB_path, sql, (survey_id,))		

def get_user(DB_path, user_id):
	sql = '''SELECT * FROM users WHERE id=?'''	
	x = __get(DB_path, sql,(user_id,))
	if len(x) > 0:
		return x[0]
	return []

def get_report(DB_path, user_id, survey_id):
	sql = '''SELECT * FROM {} WHERE user_id=? order by timestamp DESC'''.format("survey_"+survey_id)	
	return __get(DB_path, sql,(user_id,))

def get_survey(DB_path, survey_id):
	sql = '''SELECT survey FROM surveys WHERE id=? '''
	x = __get(DB_path, sql,(survey_id,))
	if len(x) > 0:
		return x[0][0]
	return []

def init(DB_path, override=False):
	"""
		Initalize backend: check if DB_path is a sqlite DB, if not create one
	"""
	if override:
		__create_DB(DB_path)	
	else:
		#create only if there is not a users table already
		if not __table_exists(DB_path, 'users'):		
			__create_DB(DB_path)	
		else:
			print "[backend @ {} already exists]".format(DB_path)		

def join_survey(DB_path, user_id, survey_id, am_check=9, pm_check=4):
	assert am_check <= 12 and am_check > 0
	assert pm_check <= 12 and pm_check > 0
	if not __table_exists(DB_path, "survey_"+survey_id):
		raise RuntimeError("survey {} not found".format(survey_id))
	row = {"user_id":user_id, "survey_id":survey_id, "am_check":am_check, "pm_check":pm_check}
	try:		
		__put(DB_path, "user_surveys", row)
	except sqlite3.IntegrityError:				
		raise RuntimeError("user {} already joined survey {}".format(user_id, survey_id))

def list_surveys(DB_path,user_id=None):	
	if user_id is None:
		sql = ''' SELECT * FROM surveys'''
		return __get(DB_path, sql)
	else:
		sql = ''' SELECT * FROM user_surveys WHERE user_id=?'''
		return __get(DB_path, sql,(user_id,))

def save_response(DB_path, survey_id, response):
	__put(DB_path, "survey_"+survey_id, response)	

def schedule_survey(DB_path, user_id, survey_id, am_check, pm_check):
	assert am_check <= 12 and am_check > 0
	assert pm_check <= 12 and pm_check > 0
	sql = '''UPDATE user_surveys SET am_check=?, pm_check=? WHERE user_id=? AND survey_id=?'''
	__update(DB_path, sql, (am_check, pm_check, user_id, survey_id))	

def toggle_user(DB_path, user_id, active=True):
	sql = '''UPDATE users SET active=? WHERE id=?'''
	__update(DB_path, sql, (active, user_id))	

def toggle_survey(DB_path, user_id, survey_id, active=True):
	sql = '''UPDATE user_surveys SET active=? WHERE user_id=? AND survey_id=?'''
	__update(DB_path, sql, (active, user_id, survey_id))
	


