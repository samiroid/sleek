import os
import pytest
import sqlite_backend as backend
import sqlite3
import sleek

DB_path="DATA/test.db"
backend.init(DB_path,override=False)
backend.create_table(DB_path, "some_table", ["a_field","b_field","sea_field"],override=True)
backend.insert_row(DB_path, "some_table", {"a_field":"a_field_1","b_field":"b_field_1","sea_field":"sea_field_1"})
backend.insert_row(DB_path, "some_table", {"a_field":"a_field_2","b_field":"b_field_2","sea_field":"sea_field_2"})
backend.insert_row(DB_path, "some_table", {"a_field":"a_field_3","b_field":"b_field_3","sea_field":"sea_field_3"})


sql = '''SELECT * FROM some_table '''
db = sqlite3.connect(DB_path)
cursor = db.cursor()	
cursor.execute(sql)
print cursor.fetchall()	
db.close()	
	

# try:
# 	os.remove(DB_path)
# except OSError:
# 	pass

# bot_name="sleek"
# api_token = os.environ.get('SLACK_BOT_TOKEN')


# print "hello"
# cfg={ 
# 	  "greet": ["ciao","oi","holla :)"],
# 	  "announce": "This is a test chat bot",
# 	  "nack": ["q?!", "no lo se","!?"],
#       "ack": ["roger","okidoki"],
# 	  "help": "Please some help!"	
# 	}
# #create Sleek instance with default config
# bot = sleek.Sleek(api_token,"bogus", DB_path)
# assert bot.greet() in sleek.default_bot_cfg["greet"]
