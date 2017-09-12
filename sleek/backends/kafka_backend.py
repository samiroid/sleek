"""
	Methods to comunicate with a Kafka server 
"""

from local_backend import Backend
from datetime import datetime
import json
from kafka import KafkaProducer
import pprint


class KafkaBackend(Backend):
	def __init__(self, confs, init=False):		
		pprint.pprint(confs)		
		self.kafka_topic = confs["kafka_topic"]
		self.team_id = confs["team_id"]
		kafka_servers = confs["kafka_servers"].split(",")
		self.kafka = KafkaProducer(bootstrap_servers=kafka_servers)
		Backend.__init__(self, confs, init)

	def save_answer(self, user_id, survey_id, answer):
		ans_id = Backend.save_answer(self, user_id, survey_id, answer)			
		dt = datetime.strptime(answer["ts"] , '%Y-%m-%d %H:%M')
		timestamp = (dt - datetime(1970, 1, 1)).total_seconds()	
		del answer["ts"]		
		payload = {
			"teamId": self.team_id,
			"userId": user_id,
			"timestamp": timestamp,
			"surveyId": survey_id,
			"responses": answer,
			"answerId": ans_id
		}
		print "[posting to kafka: {0}]".format(payload)
		self.post_kafka(json.dumps(payload))		

	def post_kafka(self, payload):						
		sent = self.kafka.send(self.kafka_topic, payload)		
		self.kafka.flush()
		print sent

		




	

