import sqlite_backend as backend


def __get_response(DB_path, survey_table, user_id, ts):
	#TODO: this unsafe
	sql = ''' SELECT * FROM {} WHERE user_id=? AND ts=? '''.format(survey_table)
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id, ts,))
	rep = cursor.fetchone()	
	db.close()	
	return rep

def get_responses(DB_path, survey_table, user_id):
	#TODO: this unsafe
	sql = ''' SELECT * FROM {} WHERE user_id=? '''.format(survey_table)
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id, ))
	rep = cursor.fetchall()	
	db.close()	
	return rep


def create_survey(survey_id, fields):

	SLEEP_SURVEY = ''' DROP TABLE IF EXISTS user_surveys; 
					   CREATE TABLE sleep_survey(user_id TEXT, 
					   							 ts INTEGER, 
										         sleep_hours INTEGER, 
										         sleep_quality INTEGER)  '''    
	
	STRESS_SURVEY = ''' CREATE TABLE stress_survey(user_id TEXT, ts INTEGER, stress_level INTEGER)  '''



def save_survey(DB_path, user_id, survey_id, timestamp, response):
	"""
		saves survey
		user_id: user id
		user_id: survey id
		response: a dictionary with the fields/values to be inserted
	"""

	if survey_id == "sleep_survey":		
		sleep_hours = response["sleep_hours"]
		sleep_quality = response["sleep_quality"]
		__save_sleep_survey(DB_path, user_id, timestamp, sleep_hours, sleep_quality)
	elif survey_id == "stress_survey":
		stress = response["stress"]
		__save_stress_survey(DB_path, user_id, timestamp, stress)
	else:
		raise NotImplementedError

def __save_sleep_survey(DB_path, user_id, timestamp, sleep_hours, sleep_quality):
	"""
		saves sleep survey			
	"""	
	
	sql = ''' INSERT INTO sleep_survey(user_id, ts, sleep_hours, sleep_quality) 
				     VALUES(?,?,?,?) '''			 
	
	assert type(sleep_hours) == int and sleep_hours >= 0 and sleep_hours < 24
	assert type(sleep_quality) == int and sleep_quality >= 1 and sleep_quality <= 5
	
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id, timestamp, sleep_hours, sleep_quality))		
	db.commit()
	db.close()

def __save_stress_survey(DB_path, user_id, timestamp, stress):
	"""
		saves sleep survey			
	"""
	
	sql = ''' INSERT INTO stress_survey(user_id, ts, stress_level) 
				     VALUES(?,?,?) '''			 
	
	assert type(stress) == int and stress >= 1 and stress <= 5
	
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql, (user_id, timestamp, stress))		
	db.commit()
	db.close()





	#create surveys table
	cursor.execute('''''')
	cursor.execute(USER_SURVEYS)
	#create sleep_survey table
	cursor.execute('''DROP TABLE IF EXISTS sleep_survey''')
	cursor.execute(SLEEP_SURVEY)
	#create stress_survey table
	cursor.execute('''DROP TABLE IF EXISTS stress_survey''')
	cursor.execute(STRESS_SURVEY)

