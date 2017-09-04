"""
	Methods to comunicate with a backend
"""

import codecs
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
	

	def __init__(self, confs, init=False):
		"""
			confs: dictionary with configurations
		"""
		self.DB_path = confs["local_DB"]				
		
		if init:
			dir_name = os.path.dirname(self.DB_path)
			if len(dir_name)>0 and not os.path.exists(dir_name):
				os.makedirs(dir_name)		
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
			raise RuntimeError("user already joined survey {}".format(survey_id))
	
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
			Save answers to survey

			Parameters
			----------
			user_id: string
				user id
			survey_id: string
				survey_id
			answer: dict
				dictionary with the answers {question_id:answer}

			Returns
			-------
			answer_id: string
				answers unique identifier (UUID)
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

	def save_reminder(self, user_id, survey_id, schedule):
		"""
			Save a new survey reminder for user `user_id`

			Parameters
			----------
			user_id: string
				user id
			survey_id: string
				survey_id
			schedule: string or `None`
				reminder time. Setting the `schedule` to `None` deletes 
				the reminders
		"""
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
		"""
			Get user `user_id` answers to survey `survey_id`

			Parameters
			----------
			user_id: string
				user id
			survey_id: string
				survey_id
		"""
		survey_table = "survey_{}".format(survey_id)
		if not self.__table_exists(survey_table):
			raise RuntimeError("survey {} does not exist".format(survey_id))
		sql = '''SELECT * FROM {} WHERE user_id=? order by ts DESC'''.format(survey_table)
		return self.__get(sql,(user_id,))

	def get_notes(self, user_id, survey_id):
		"""
			Get user's `user_id` notes to survey `survey_id`

			Parameters
			----------
			user_id: string
				user id
			survey_id: string
				survey_id
		"""
		survey_table = "survey_{}".format(survey_id)
		if not self.__table_exists(survey_table):
			raise RuntimeError("survey {} does not exist".format(survey_id))
		sql = '''SELECT ts, notes FROM {} WHERE user_id=? AND notes IS NOT NULL order by ts DESC'''.format(survey_table)
		return self.__get(sql,(user_id,))

	#################################################################
	# OTHER 
	#################################################################	

	def dump_surveys(self, path):
		"""
			Dump survey tables. \n
			Each table will be serialized to a file with the table name (e.g. survey_stress.txt)
			
			Parameters
			-----------
			path: string
				path to output folder 
		"""
		surveys = self.list_surveys()

		dir_name = os.path.dirname(path)
		print dir_name		
		if not os.path.exists(dir_name):
			os.makedirs(dir_name)
		
		for s in surveys:
			survey_id = s[0]
			getter = "SELECT * FROM survey_{}".format(survey_id)			
			data = self.__get(getter)
			if len(data)>0:				
				print "[getting: {}]".format(getter)
				# print data
				this_path="{}survey_{}.txt".format(path,survey_id)
				with codecs.open(this_path,"w") as f:
					for d in data:
						#replace None with empty string						
						nd = map(lambda x:"" if x is None else x, d)
						row = u"\t".join(nd[1:])
						print "\t[writing: {}]".format(row)						
						f.write(row+"\n")
				print "\n"			

	def load_surveys(self, path):
		"""
			Loads surveys in batch mode

			Parameters
			-----------
			path: string
				path to folder containing surveys in json format.
		"""
		print "[loading surveys @ {}]".format(path)
		ignored = []
		for fname in os.listdir(path):	
			abs_path = path+fname
			if os.path.splitext(abs_path)[1]!=".json":
				ignored.append(fname)			
				continue	
			try:		
				with open(abs_path, 'r') as f:					
					try:
						survey = json.load(f)				
					except ValueError:
						print "invalid json @{}".format(fname)
						continue
					try:
						self.create_survey(survey)		
						print "\t>" + fname	
					except RuntimeError as e:
						print e
			except IOError:
				ignored.append(abs_path)	
		if len(ignored) > 0:
			print "[ignored the files: {}]".format(repr(ignored))