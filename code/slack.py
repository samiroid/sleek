from ipdb import set_trace
from slackclient import SlackClient
import time
from random import randint
import sqlite_backend as backend
from sleek import Sleek
import json

READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose

def __is_valid_schedule(s):
		if not s.replace('.','',1).isdigit():
			return False
		else:
			t = int(s)
			if t < 1 or t > 12:
				return False
		return True

class Sleek4Slack(Sleek):
	sleek_announce = ''' Hello I am Sleek4Slack, the chat bot :) '''
	
	sleek_help = ''' This a list of the commands I already know:				      
- toggle [yes|out]: to set 
- delete [survey]: delete all the answers to survey
- delete: delete all the answers to ALL the surveys 				    
- join [survey]: to join survey [survey] 				      
- leave [survey]: to leave survey [survey] 
- list: see a list of surveys				      				      
- reschedule [survey]: to reschudle survey [survey] 
- report [survey]: to see a report with all the answers to survey [survey]			
				'''
	
	default_cfg={
				"announce": sleek_announce,				
				"help": sleek_help,
				"nack": ["sorry, I didn't get that", "I don't understand that command","!?"]
				}

	def __init__(self, api_token, DB_path, bot_name, cfg=default_cfg):
		Sleek.__init__(self, cfg)
		self.slack_client = SlackClient(api_token)
		self.DB_path = DB_path
		backend.init(DB_path, override=False)
		self.available_surveys = {x[0]:json.loads(x[1]) for x in backend.list_surveys(DB_path)}
		self.bot_id = None
		#maps usernames to ID's
		self.users = self.__retrieve_members() 

		if bot_name not in self.users:
			raise RuntimeError("Could not find bot @{} ID")	
		else:			
			self.bot_id = self.users[bot_name].lower()
			print "[bot_id: #{}]".format(self.bot_id)		

	def __retrieve_members(self):
		resp = self.slack_client.api_call("users.list")
		users = {}
		if resp.get('ok'):
			# retrieve all users
			members = resp.get('members')
			for user in members:
				#ignore slackbot
				if 'name' not in user or user.get('id') == "USLACKBOT": continue				
				users[user.get('name')] = user.get('id')							
		else:
			raise RuntimeError("Could not retrieve members list\n{}".format(resp))
		return users

	def __retrieve_IMs(self):
		resp = self.slack_client.api_call("im.list")
		ims = {}
		if resp.get('ok'):
			for im in resp['ims']:
				if not im['is_user_deleted']:
					ims[im['user']] = im['id']
		else:			
			raise RuntimeError("Could not retrieve IMs list\n{}".format(resp))
		return ims

	def __delete(self, command, context):
		user_id = context["user"]
		# DOC
		try:
			survey = command[1]
			return "You wanted to delete all your answers to survey {}? Sorry, this is not implemented yet...".format(survey)				
		except IndexError:
			backend.delete_user(self.DB_path, user_id)			
			return "I deleted all your surveys data.\n Hope you come back soon..."

	def __join(self, command, context):
		user_id = context["user"]
		if len(command) == 1:
			ack = "Welcome Back!"
			#no parameters were given
			backend.toggle_user(self.DB_path, user_id, active=True)
			return ack
		else:		
			ack = "You joined survey {}. I will remind you to fill it at {} AM and then at {} PM"	
			survey_id = command[1]			
			am_check  = command[2]			
			pm_check  = command[3]						
			backend.join_survey(self.DB_path, user_id, survey_id, am_check, pm_check)
			return ack.format(survey_id, am_check, pm_check)	

	def __leave(self, command, context):
		user_id = context["user"]
		if len(command) == 1:
			ack = "Hope to see you soon! If you decide just use the 'join' command. Don't worry, I will keep all of your data. "
			backend.toggle_user(self.DB_path, user_id, active=False)
			return ack
		else:			
			survey_id = command[1]			
			am_check  = command[2]			
			pm_check  = command[3]						
			backend.join_survey(self.DB_path, user_id, survey_id, am_check, pm_check)
			return "You joined survey {}. I will remind you to fill it at {} AM and then at {} PM".format(survey_id, am_check, pm_check)	

	def __list(self, command, context):
		user_id = context["user"]
		surveys = backend.list_surveys(self.DB_path, user_id)
		return surveys

	def __report(self, command, context):
		user_id = context["user"]
		survey_id = command[1]
		return backend.get_report(self.DB_path, user_id, survey_id)

	def __schedule(self, command, context):
		ack = "Done! I scheduled survey {} to {} AM and {} PM "		
		nack = "Oops the command {} is invalid {} \n Try *schedule [survey] [AM] [PM]"
		user_id = context["user"]
		if len(command) < 4:
			err = "(insufficient arguments)"
			return nack.format(err," ".join(command))		
		survey_id = command[1]		
		am_check  = command[2]	
		pm_check  = command[3]								
		if not __is_valid_schedule(am_check):
			err = "(AM invalid)"
			return nack.format(err," ".join(command))

		if not __is_valid_schedule(pm_check):
			err = "(PM invalid)"
			return nack.format(err," ".join(command))
		
		backend.schedule_survey(self.DB_path, user_id, survey_id, am_check, pm_check)
		return ack.format(survey_id, am_check, pm_check)

	def chat(self, text_input, context):
		command = text_input.split()
		user_id = context["user"]
		print "[command: {}({}) | user: {}]".format(command[0],repr(command[1:]), user_id)
		if command[0] == "delete":		
			resp = self.__delete(command, context)
		elif command[0] == "join":
			resp = self.__join(command, context)
		elif command[0] == "leave":			
			resp = self.__leave(command, context)								
		elif command[0] == "list":			
			resp = self.__list(command, context)						
		elif command[0] == "report":			
			resp = self.__report(command, context)								
		elif command[0] == "schedule":			
			resp = self.__schedule(command, context)								
		else:
			resp = Sleek.chat(self, text_input, context)
		return resp

	def connect(self, channel, dbg=False):		
		if self.slack_client.rtm_connect():			
			post = self.greet()
			self.post_channel(channel, post)
			while True:
				resp = self.slack_client.rtm_read()		
				if resp and len(resp) > 0:
					for output in resp:
						if not 'text' in output: continue
						if dbg: print "dbg: {}\n".format(repr(output))
						try:							
							text = output['text'].strip().lower()
						   	ts = output['ts']
						   	channel = output['channel']
						   	user = output['user']
						   	#only react to messages directed at the bot						   	
						   	if "<@{}>".format(self.bot_id) in text: 
						   		#do stuff here
						   		#remove bot mention
						   		text = text.replace("<@{}>".format(self.bot_id),"")
					   			reply = self.chat(text, {"user":user,"ts":ts,"channel":channel})
					   			self.post_channel(channel, reply)
						   	time.sleep(READ_WEBSOCKET_DELAY)
					   	except KeyError:
					   		pass				
		else:
			raise RuntimeError("Could not connect to RTM API")

	def delete_survey(self, survey_id):
		"""
			Delete a survey
			survey_id: survey id
		"""
		backend.delete_survey(self.DB_path, survey_id)
	
	def elicit():
		raise NotImplementedError	

	def get_response():
		raise NotImplementedError

	def post_channel(self, channel, message):
		print "[posting:\"{}\" to channel {}]".format(message,channel)
		resp = self.slack_client.api_call("chat.postMessage",
  					 channel=channel,
  					 as_user=True,
  					 text=message)
		if not resp.get("ok"):
			print "\033[31m[error: {}]\033[0m".format(resp["error"])

	def post_IM(self, user, message):
		im_id = self.ims[self.users[user]]
		print "[posting:\"{}\" to user @{} (IM:{})]".format(message,user,im_id)
		print self.slack_client.api_call("chat.postMessage",
										 channel="{}".format(im_id),
										 as_user=True,
										 text=message)

	def upload_survey(self, survey):
		"""
			Create a survey
			survey: survey
		"""
		backend.create_survey(self.DB, survey)


	
	
	
		

	
	

	
	
