import os
import pytest
import sqlite_backend as backend
import sqlite3

DB_path="DATA/test.db"

try:
	os.remove(DB_path)
except OSError:
	pass

def table_exists(DB_path, table_name):
	"""
		Auxiliary method to check if a table exists
	"""	
	check_table_sql = ''' SELECT count(*) FROM sqlite_master WHERE type='table' AND name=? '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(check_table_sql,(table_name,))
	v = cursor.fetchone()[0]
	db.close()
	return v == 1

def test_table_exists():	
	assert not table_exists(DB_path, "users")	
	USERS = ''' CREATE TABLE users(user_id TEXT PRIMARY KEY, username TEXT, active INTEGER DEFAULT 1) '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()		
	cursor.execute(USERS)		
	db.commit()	
	db.close()
	assert table_exists(DB_path, "users")


def test_add_user():
	#create DB
	backend.init(DB_path,override=True)
	#create user with default check times
	user_1="alice"
	id_1="123"
	backend.add_user(DB_path, id_1, user_1)
	#create user with specific check times
	user_2="bob"
	id_2="456"	
	backend.add_user(DB_path, id_2, user_2)	
	#check that user_1 was correctly created
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE user_id=? '''
	cursor.execute(sql, (id_1,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == id_1 and \
		   resp[backend.USER_NAME] == user_1
	#check that user_2 was correctly created
	cursor.execute(sql, (id_2,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]  == id_2 and \
	       resp[backend.USER_NAME] == user_2 and \
	       resp[backend.USER_ACTIVE] == 1
	#remove test DB
	os.remove(DB_path)

def test_create_table():
	#create DB
	backend.init(DB_path, override=True)	
	fields = ["some_field", "another_field","yet_another_field", "final_field"]
	assert not table_exists(DB_path, "some_table")
	#create table
	backend.create_table(DB_path, "some_table", fields)
	#check if table exists	
	assert table_exists(DB_path, "some_table")	
	#try to create table with the same name *without* ovrride	
	with pytest.raises(sqlite3.OperationalError):
		backend.create_table(DB_path, "some_table", fields, override=False)	
	#try to create table with the same name *with* ovrride		
	backend.create_table(DB_path, "some_table", fields, override=True)	
	#check if table exists
	assert table_exists(DB_path, "some_table")	
	#remove test DB
	os.remove(DB_path)

def test_delete_user():
	#create DB
	backend.init(DB_path,override=True)
	#create user 
	username="alice"
	user_id="123"
	backend.add_user(DB_path, user_id, username)			
	#check that user was correctly created
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE user_id=? '''
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == user_id and \
		   resp[backend.USER_NAME] == username and \
	       resp[backend.USER_ACTIVE] == 1
	#remove user
	backend.delete_user(DB_path, user_id)
	#check user does not exist
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp is None	
	#remove test DB
	os.remove(DB_path)

def test_get_user():
	#create DB
	backend.init(DB_path,override=True)
	#create user 
	username="alice"
	user_id="123"
	backend.add_user(DB_path, user_id, username)			
	#check that user was correctly created
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()
	sql = ''' SELECT * FROM users WHERE user_id=? '''
	cursor.execute(sql, (user_id,))
	resp = cursor.fetchone()	
	assert resp[backend.USER_ID]   == user_id and \
		   resp[backend.USER_NAME] == username and \
	       resp[backend.USER_ACTIVE] == 1
	#load user
	user = backend.get_user(DB_path, user_id)
	assert user[backend.USER_ID]   == user_id and \
		   user[backend.USER_NAME] == username and \
	       resp[backend.USER_ACTIVE] == 1
	#remove test DB
	os.remove(DB_path)

# def test_get_users():
# 	assert False == True
	
def test_init():	
	#check that DB does not exit
	assert not os.path.isfile(DB_path)
	#create DB
	backend.init(DB_path,override=True)
	assert os.path.isfile(DB_path)
	#insert a few rows into the users table
	backend.insert_row(DB_path, "users", {"user_id":"1","username":"user 1"})
	backend.insert_row(DB_path, "users", {"user_id":"2","username":"user 2"})
	backend.insert_row(DB_path, "users", {"user_id":"3","username":"user 3"})
	#make sure rows are preserved
	sql = '''SELECT * FROM users '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql)
	resp =  cursor.fetchall()	
	assert resp[0] == (u'1', u'user 1',1) 
	assert resp[1] == (u'2', u'user 2',1) 
	assert resp[2] == (u'3', u'user 3',1)
	#create the same DB *without* override	
	backend.init(DB_path,override=False)
	sql = '''SELECT * FROM users '''	
	cursor.execute(sql)
	resp_2 =  cursor.fetchall()	
	assert resp_2[0] == (u'1', u'user 1',1) 
	assert resp_2[1] == (u'2', u'user 2',1) 
	assert resp_2[2] == (u'3', u'user 3',1)
	#create the same DB *with* override
	backend.init(DB_path,override=True)
	#make sure the users table is empty
	cursor.execute(sql)
	resp_3 =  cursor.fetchall()	
	assert resp_3 == []
	os.remove(DB_path)

def test_insert_row():
	#create the same DB *with* override
	backend.init(DB_path,override=True)
	backend.create_table(DB_path, "some_table", ["a_field","b_field","sea_field"],override=True)
	backend.insert_row(DB_path, "some_table", {"a_field":"a_field_1","b_field":"b_field_1","sea_field":"sea_field_1"})
	backend.insert_row(DB_path, "some_table", {"a_field":"a_field_2","b_field":"b_field_2","sea_field":"sea_field_2"})
	backend.insert_row(DB_path, "some_table", {"a_field":"a_field_3","b_field":"b_field_3","sea_field":"sea_field_3"})
	sql = '''SELECT * FROM some_table '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql)
	resp =  cursor.fetchall()	
	assert resp[0] == (u'a_field_1', u'b_field_1', u'sea_field_1') 
	assert resp[1] == (u'a_field_2', u'b_field_2', u'sea_field_2') 
	assert resp[2] == (u'a_field_3', u'b_field_3', u'sea_field_3')
	os.remove(DB_path)		

def test_update_user():
	"""
		assumes add_user() and get_user() are correct
	"""
	#create DB
	backend.init(DB_path,override=True)
	#create user 
	username="alice"
	user_id="123"	
	backend.add_user(DB_path, user_id, username)			
	user = backend.get_user(DB_path, user_id)
	#check initial values
	assert user[backend.USER_NAME] == username	
	#update username
	nu_username="bob"
	backend.update_user(DB_path, user_id,new_username=nu_username)
	user = backend.get_user(DB_path, user_id)	
	assert user[backend.USER_NAME] == nu_username 		   
	#remove test DB
	os.remove(DB_path)

def test_toggle_user():
	backend.init(DB_path,override=True)
	#create user	
	backend.add_user(DB_path, "user_id", "username")	
	#check it's active
	user = backend.get_user(DB_path, "user_id")
	assert user[backend.USER_ACTIVE] == 1
	#disable user
	backend.toggle_user(DB_path, "user_id",active=False)
	#check it's inactive
	user = backend.get_user(DB_path, "user_id")
	assert user[backend.USER_ACTIVE] == 0
	#enable user
	backend.toggle_user(DB_path, "user_id",active=True)
	#check it's active
	user = backend.get_user(DB_path, "user_id")
	assert user[backend.USER_ACTIVE] == 1
	os.remove(DB_path)

def test_toggle_survey():
	backend.init(DB_path,override=True)
	#create user	
	#user_id TEXT, survey_table TEXT, am_check TEXT, pm_check TEXT, active INTEGER DEFAULT 1
	survey = {"user_id":"1","survey_id":"some_survey","pm_check":"1","am_check":"2"}
	backend.insert_row(DB_path, "user_surveys", survey)
	#check it's *active*
	sql = '''SELECT * FROM user_surveys '''
	db = sqlite3.connect(DB_path)
	cursor = db.cursor()	
	cursor.execute(sql)
	resp =  cursor.fetchone()		
	assert resp[backend.SURVEYS_ACTIVE] == 1
	#disable user survey
	backend.toggle_survey(DB_path, "1", "some_survey",active=False)
	#check it's *inactive*
	cursor.execute(sql)
	resp =  cursor.fetchone()		
	assert resp[backend.SURVEYS_ACTIVE] == 0

	#enable user survey
	backend.toggle_survey(DB_path, "1", "some_survey",active=True)
	#check it's *active* again
	cursor.execute(sql)
	resp =  cursor.fetchone()		
	assert resp[backend.SURVEYS_ACTIVE] == 1


