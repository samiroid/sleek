"""
	Methods to comunicate with a backend
"""

from datetime import datetime
import json
import os
import sqlite3
import uuid

try:
	from ipdb import set_trace
except ImportError:
	from pdb import set_trace

class Backend(object):
	#user table columns
	USER_ID = 0
	USER_ACTIVE = 1

	#user_surveys table columns
	SURVEYS_USER_ID = 0
	SURVEYS_ID = 1
	SURVEYS_AM_REMINDER = 2
	SURVEYS_PM_REMINDER = 3

	def __init__(self, cfg, init=False):
		"""
			cfg: dictionary with configurations
		"""
		self.DB_path = cfg["local_DB"]
		dir_name = os.path.dirname(self.DB_path)

		if not os.path.exists(dir_name):
			os.makedirs(dir_name)		

		if init:
			self.__create_DB()

	#################################################################
	# PRIVATE METHODS
	#################################################################

	def __create_DB(self):
		"""
			Create database with tables 'users' and 'surveys' and 'user_surveys'
		"""
		USERS =        ''' CREATE TABLE users(id TEXT PRIMARY KEY, 
											  active INTEGER DEFAULT 1) '''
		
		USER_SURVEYS = ''' CREATE TABLE user_surveys(user_id TEXT, survey_id TEXT, 
											         am_reminder TEXT, pm_reminder TEXT, 
											         PRIMARY KEY(user_id, survey_id))  '''

		SURVEYS = ''' CREATE TABLE surveys(id TEXT PRIMARY KEY, survey TEXT)  '''

		try:
			#try to remove the file
			os.remove(self.DB_path)
		except:
			pass

		db = sqlite3.connect(self.DB_path)
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

	def __get(self, sql, params=None):
		db = sqlite3.connect(self.DB_path)
		cursor = db.cursor()	
		if params is not None: cursor.execute(sql, tuple(params))
		else:                  cursor.execute(sql)
		res = cursor.fetchall()	
		db.close()	
		return res

	def __update(self, sql, params):
		db = sqlite3.connect(self.DB_path)
		cursor = db.cursor()		
		cursor.execute(sql, params)
		rc = cursor.rowcount
		db.commit()
		db.close()
		return rc

	def __put(self, table_name, row):
		"""
			row is a dictionary: {column: value}
		"""	
		db = sqlite3.connect(self.DB_path)
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

	def __table_exists(self, table_name):
		"""
			Auxiliary method to check if a table exists
		"""	
		check_table_sql = ''' SELECT count(*) FROM sqlite_master WHERE type='table' AND name=? '''
		t = self.__get(check_table_sql,(table_name,))[0][0]
		return t == 1

	#################################################################
	# USER METHODS
	#################################################################

	def add_user(self, user_id):
		row = {"id":user_id}		
		try:
			return self.__put("users", row) > 0
		except sqlite3.IntegrityError:
			return False

	def get_users(self, user_id=None):
		params = None
		if user_id is None:
			sql = '''SELECT * FROM users WHERE id=?'''	
			params = (user_id,)
		else:
			sql = '''SELECT * FROM users'''	
		return self.__get(sql, params)			
		
	def toggle_user(self, user_id, active=True):
		sql = '''UPDATE users SET active=? WHERE id=?'''
		return self.__update(sql, (active, user_id)) > 0	

	#################################################################
	# SURVEY METHODS
	#################################################################

	def create_survey(self, survey):
		table_name = "survey_"+survey["id"]	
		fields = ["user_id","ts"] + [q["q_id"] for q in survey["questions"] ] + ["notes"]
		try:
			self.__put("surveys", {"id":survey["id"],"survey":json.dumps(survey)})
			db = sqlite3.connect(self.DB_path)
			cursor = db.cursor()			
			sql_fields = 'ID TEXT PRIMARY KEY, ' + ' TEXT, '.join(fields) + ' TEXT' 
		 	create = ''' CREATE TABLE {}({}) '''.format(table_name, sql_fields)
			#create table		
			cursor.execute(create)	
			db.commit()
			db.close()
		except sqlite3.IntegrityError: 
			raise RuntimeError("survey {} already exists".format(survey["id"].upper()))

	def delete_answers(self, user_id, survey_id):
		sql = '''DELETE FROM survey_{} WHERE user_id=?'''.format(survey_id)
		return self.__update(sql, (user_id,)) > 0
	
	def get_survey(self, survey_id):
		sql = '''SELECT survey FROM surveys WHERE id=? '''
		x = self.__get(sql,(survey_id,))
		if len(x) > 0: return json.loads(x[0][0])
		else:          return None

	def join_survey(self, user_id, survey_id):	
		if not self.__table_exists("survey_"+survey_id):
			raise RuntimeError("survey {} not found".format(survey_id))	
		self.add_user(user_id)	
		row = {"user_id":user_id, "survey_id":survey_id}
		try:		
			return self.__put("user_surveys", row) > 0
		except sqlite3.IntegrityError:				
			raise RuntimeError("user {} already joined survey {}".format(user_id, survey_id))
	
	def list_surveys(self, user_id=None):	
		if user_id is None:
			sql = ''' SELECT * FROM surveys'''
			return self.__get(sql)
		else:
			sql = ''' SELECT * FROM user_surveys WHERE user_id=?'''
			return self.__get(sql,(user_id,))

	def leave_survey(self, user_id, survey_id):
		sql = '''DELETE FROM user_surveys WHERE user_id=? and survey_id=?'''.format(survey_id)
		return self.__update(sql, (user_id, survey_id)) > 0

	def save_answer(self, user_id, survey_id, answer):
		"""
			row is a dictionary: {column: value}
		"""
		ans_id = uuid.uuid4().hex
		answer["user_id"] = user_id		
		answer["id"] = ans_id
		survey_table = "survey_{}".format(survey_id)
		self.__put(survey_table, answer)
		return ans_id

	#################################################################
	# REMINDER METHODS
	#################################################################

	# def get_reminders(self):
	# 	sql = '''SELECT * FROM user_surveys'''
	# 	return  self.__get(sql)

	def get_reminders(self, user_id=None):
		if user_id is None:
			sql = ''' SELECT * FROM user_surveys'''
			return self.__get(sql)
		else:
			sql = ''' SELECT survey_id, am_reminder, pm_reminder FROM user_surveys WHERE user_id=?'''
			return self.__get(sql,(user_id,))

	def save_reminder(self, user_id, survey_id, schedule):
		if schedule is None:
			sql = '''UPDATE user_surveys SET am_reminder=NULL, pm_reminder=NULL WHERE user_id=? AND survey_id=?'''
			params = (user_id, survey_id,)
		elif "am" in schedule.lower():
			sql = '''UPDATE user_surveys SET am_reminder=? WHERE user_id=? AND survey_id=?'''
			params = (schedule, user_id, survey_id,)
		elif "pm" in schedule.lower():
			sql = '''UPDATE user_surveys SET pm_reminder=? WHERE user_id=? AND survey_id=?'''
			params = (schedule, user_id, survey_id,)
		else:
			raise NotImplementedError
		return self.__update(sql, params)	

	#################################################################
	# REPORT METHODS
	#################################################################	

	def get_report(self, user_id, survey_id):
		survey_table = "survey_{}".format(survey_id)
		if not self.__table_exists(survey_table):
			raise RuntimeError("survey does not exist")
		sql = '''SELECT * FROM {} WHERE user_id=? order by ts DESC'''.format(survey_table)
		return self.__get(sql,(user_id,))

	def get_notes(self, user_id, survey_id):
		survey_table = "survey_{}".format(survey_id)
		if not self.__table_exists(survey_table):
			raise RuntimeError("survey does not exist")
		sql = '''SELECT ts, notes FROM {} WHERE user_id=? AND notes IS NOT NULL order by ts DESC'''.format(survey_table)
		return self.__get(sql,(user_id,))


		




	

