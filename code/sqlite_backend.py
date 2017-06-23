"""
	Methods to comunicate with a backend
"""

import sqlite3
#from ipdb import set_trace

#user table columns
USER_ID = 0
USER_NAME = 1
USER_ACTIVE = 2

#user surveys table columns
SURVEYS_USER_ID = 0
SURVEYS_ID = 1
SURVEYS_AM_CHECK = 2
SURVEYS_PM_CHECK = 3
SURVEYS_ACTIVE = 4

def __create_DB(DB_path, override=False):
	"""
		Create database with tables 'users' and 'surveys'
	"""
	USERS =        ''' CREATE TABLE users(user_id TEXT PRIMARY KEY, username TEXT, active INTEGER DEFAULT 1) '''
	
	USER_SURVEYS = ''' CREATE TABLE user_surveys(user_id TEXT, survey_id TEXT, 
										         am_check TEXT, pm_check TEXT, active INTEGER DEFAULT 1)  '''

	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	#create users table
	cursor.execute(''' DROP TABLE IF EXISTS users; ''')	
	cursor.execute(USERS)	
	#create users table
	cursor.execute(''' DROP TABLE IF EXISTS user_surveys; ''')
	cursor.execute(USER_SURVEYS)
	db.commit()
	db.close()	

def add_user(DB_path, user_id, username):
	insert_row(DB_path, "users", {"user_id":user_id,"username":username})

def create_table(DB_path, table_name, fields, override=False):	
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

def delete_user(DB_path, user_id):
	sql = '''DELETE FROM users WHERE user_id=?'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id,))
	db.commit()
	db.close()

def get_user(DB_path, user_id):
	sql = '''SELECT * FROM users WHERE user_id=?'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id,))
	user = cursor.fetchone()	
	db.close()	
	return user

def init(DB_path, override=False):
	"""
		Initalize backend: check if DB_path is a sqlite DB, if not create one
	"""
	if override:
		__create_DB(DB_path)	
	else:
		#check if there is a users table
		check_table_sql = ''' SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users' '''
		db = sqlite3.connect(DB_path)
		cursor = db.cursor()	
		cursor.execute(check_table_sql)
		if cursor.fetchone()[0]	== 0:
			__create_DB(DB_path)	
		db.close()	

def insert_row(DB_path, table_name, row):
	"""
		row is a dictionary: {column: value}
	"""
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	

	#old_sql_insert = ''' INSERT OR IGNORE INTO surveys(user_id, day, period) VALUES(?,?,?) '''			 
	
	keys = row.keys()
	values = row.values()
	sql_keys = ','.join(keys)
	sql_values =  ('?,'*len(values)).strip(',')
	sql_insert = ''' INSERT INTO {}({}) VALUES({}) '''.format(table_name,sql_keys,sql_values)
	cursor.execute(sql_insert, values)		
	db.commit()
	db.close()

# def insert_row(DB_path, sql, params):

# 	db = sqlite3.connect(DB_path)
# 	cursor = db.cursor()	
# 	cursor.execute(sql, params)		
# 	db.commit()
# 	db.close()

# def remove_user(DB_path, user_id, survey_id, cascade=False):
# 	"""
# 		removes user from survey
# 		cascade == True also deletes any existing survey entries
# 	"""
# 	if cascade == True:
# 		raise NotImplementedError
# 	sql = '''DELETE FROM user_surveys WHERE user_id=?'''
# 	db = sqlite3.connect(DB_path)
# 	cursor = db.cursor()	
# 	cursor.execute(sql, (user_id,))
# 	db.commit()
# 	db.close()

def update_user(DB_path, user_id, new_username=None):
	sql = '''UPDATE users SET username=? WHERE user_id=?'''
	#load current values
	user = get_user(DB_path, user_id)
	if new_username is not None:
		username=new_username
	else:
		username=user[USER_NAME]
	
	#update user	
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	cursor.execute(sql, (username, user_id,))	
	db.commit()
	db.close()	


def toggle_user(DB_path, user_id, active=True):
	sql = '''UPDATE users set active=? WHERE user_id=?'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (active, user_id))
	db.commit()
	db.close()

def toggle_survey(DB_path, user_id, survey_id, active=True):
	sql = '''UPDATE user_surveys set active=? WHERE user_id=? AND survey_id=?'''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (active, user_id, survey_id))
	db.commit()
	db.close()


# def create_table(DB_path, table_name, sql, override=False):	
# 	db = sqlite3.connect(DB_path)
# 	cursor = db.cursor()
# 	if override:
# 		 drop = ''' DROP TABLE IF EXISTS {} '''.format(table_name)
# 		 cursor.execute(drop)	
# 	#create table	
# 	cursor.execute(sql)	
# 	db.commit()
# 	db.close()	


# def get_users(DB_path):
# 	sql = '''SELECT * FROM users'''
# 	db = sqlite3.connect(DB_path)
# 	cursor = db.cursor()	
# 	cursor.execute(sql)
# 	users = cursor.fetchall()
# 	db.close()	
# 	return users







# def __create_DB(DB_path):
# 	"""
# 		Create database with tables 'users' and 'surveys'
# 	"""
# 	USERS_TABLE = ''' CREATE TABLE users(user_id TEXT PRIMARY KEY, 
# 									   am_check INTEGER, pm_check INTEGER) '''
# 	sql_surveys = ''' CREATE TABLE surveys(user_id TEXT, day TEXT, 
# 										   period TEXT, sleep_hours INTEGER, 
# 										   sleep_quality INTEGER, stress INTEGER,
# 										   PRIMARY KEY (user_id, day, period),
# 										   FOREIGN KEY (user_id) REFERENCES users(user_id)) '''
# 	db = sqlite3.connect(DB_path)
# 	cursor = db.cursor()
# 	#create users table
# 	cursor.execute('''DROP TABLE IF EXISTS users''')
# 	cursor.execute(sql_users)
# 	db.commit()
# 	#create surveys table
# 	cursor.execute('''DROP TABLE IF EXISTS surveys''')
# 	cursor.execute(sql_surveys)
# 	db.commit()
# 	db.close()

# def upsert_survey(DB_path, user_id, day, period, sleep_hours=None, sleep_quality=None, stress=None):
# 	assert period is not None and period.upper() in ["AM","PM"]
# 	sql_update = '''UPDATE surveys SET {}
# 			 WHERE user_id=? AND day=? AND period=?'''
# 	sql_insert = ''' INSERT OR IGNORE INTO surveys(user_id, day, period) 
# 				     VALUES(?,?,?) '''			 
# 	valz=[]
# 	fields=""
# 	if sleep_hours is not None:
# 		assert type(sleep_hours) == int and \
# 			   sleep_hours >= 0 and sleep_hours < 24
# 		fields+="sleep_hours=?," 
# 		valz+=[sleep_hours]	
	
# 	if sleep_quality is not None:
# 		assert type(sleep_quality) == int and \
# 			   sleep_quality >= 1 and sleep_quality <= 5
# 		fields+="sleep_quality=?," 
# 		valz+=[sleep_quality]
	
# 	if stress is not None:
# 		assert type(stress) == int and \
# 			   stress >= 1 and stress <= 5
# 		fields+="stress=?," 
# 		valz+=[stress]

# 	assert len(valz)>0	
# 	valz+=[user_id, day, period]
# 	db = sqlite3.connect(DB_path)
# 	cursor = db.cursor()	
# 	cursor.execute(sql_insert, (user_id, day, period,))	
# 	cursor.execute(sql_update.format(fields.rstrip(",")), tuple(valz))
# 	db.commit()
# 	db.close()
