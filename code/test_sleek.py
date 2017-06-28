import os
import pytest
import sqlite_backend as backend
import sqlite3
import sleek

DB_path="DATA/test.db"

try:
	os.remove(DB_path)
except OSError:
	pass

bot_name="sleek"
api_token = os.environ.get('SLACK_BOT_TOKEN')

def test_chatBot():
	print "hello"
	cfg={ 
		  "greet": ["ciao","oi","holla :)"],
		  "announce": "This is a test chat bot",
		  "nack": ["q?!", "no lo se","!?"],
	      "ack": ["roger","okidoki"],
		  "help": "Please some help!"	
		}
	#create Sleek instance with default config
	bot = sleek.Sleek(api_token,"bogus", DB_path)
	assert bot.greet() in sleek.default_cfg["greet"]
	assert bot.ack() in sleek.default_cfg["ack"]
	assert bot.nack() in sleek.default_cfg["nack"]
	assert bot.announce() == sleek.default_cfg["announce"]
	assert bot.help() == sleek.default_cfg["help"]

	#create Sleek instance with custom config
	bot2 = sleek.Sleek(api_token, bot_name, DB_path, cfg=cfg)
	assert bot2.greet() in cfg["greet"]
	assert bot2.ack() in cfg["ack"]
	assert bot2.nack() in cfg["nack"]
	assert bot2.help() in cfg["help"]
	assert bot2.announce() in cfg["announce"]
	os.remove(DB_path)

def test_chat():
	assert True == False
	


