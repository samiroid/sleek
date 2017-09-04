from ipdb import set_trace
import json
import pytest
import sys
import sqlite3
sys.path.insert(0,'..')
from sleek import KafkaBackend as Backend
from kafka import KafkaConsumer

DB_path="test.db"

cfg = {
		"local_DB":DB_path,
		"kafka_servers":"localhost",
		"kafka_topic":"dummy",
		"team_id":"team"
		}
user_id="SILVIO"

COL_USER_ID = 0
COL_USER_ACTIVE = 1

sleep_survey = { "id": "sleep",
	 				  "questions": [  { "q_id": "sleep_hours",
	       							  	"question": "how many hours have you slept yesterday?",
		       						   	"choices": ["<4", 4, 5, 6, 7, 8, ">8"]},
		    						{ "q_id": "sleep_quality",
		       						  "question": "In a scale from 1 to 5, how do you rate the quality of your sleep?",
		       						  "choices": [1,2,3,4,5] }  
		       					]
					}
	 
stress_survey = { "id": "stress",
 				  "questions": [  {"q_id": "stress_level",
	       							"question": "In a scale from 1 to 5, how do you rate your stress level ?",
	       							"choices": [1,2,3,4,5] } ]}


if __name__ == "__main__":
	my_backend = Backend(cfg, create=True)	
	my_backend.create_survey(sleep_survey)				
	consumer = KafkaConsumer(cfg["kafka_topic"], bootstrap_servers=cfg["kafka_servers"].split(), auto_offset_reset='earliest')
	#save answer
	ans = {"sleep_hours":9,"sleep_quality":5, "ts": 200}
	my_backend.save_answer(user_id, sleep_survey["id"], ans)	
	s = consumer.next().value
	print s
	r = json.loads(s)["responses"]	
	assert r == ans
