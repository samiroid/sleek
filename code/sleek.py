from ipdb import set_trace
from slackclient import SlackClient
import time
from random import randint
import sqlite_backend as backend

READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose

default_bot_cfg={
	"greet": ["hi","yo","hello :)"],
	"announce": "Hello I am a chatbot but I can't do much yet...",
	"nack": ["sorry I didn't get that", "I don't understand that command","!?"],
	"ack": ["ok","got it!","sure","no problem"],
	"help": "A little help"	
}

class ChatBot(object): 
	
	def __init__(self, cfg=None):		

		self.__greets = None
		self.__acks = None
		self.__nacks = None
		self.__help = None
		self.__announce = None

		if cfg is None:
			print "[starting bot with default confs]"
			self.__load_cfg(default_bot_cfg)
		else:
			print "[loading confs]"
			self.__load_cfg(cfg)

	def __load_cfg(self, cfg):
		"""
			Load bot configuration. Any 
			cfg: dictionary with the following fields: greetings, acks, nacks, help
		"""

		# values not present in the config dictionary will be replaced with default values 
		try:
			self.__greets = cfg["greet"]
		except KeyError:
			self.__greets = default_bot_cfg["greet"]

		try:
			self.__acks = cfg["ack"]
		except KeyError:
			self.__acks = default_bot_cfg["ack"]
		
		try:
			self.__nacks = cfg["nack"]
		except KeyError:
			self.__nacks = default_bot_cfg["nack"]

		try:
			self.__help = cfg["help"]
		except KeyError:
			self.__help = default_bot_cfg["help"]

		try:
			self.__announce = cfg["announce"]
		except KeyError:
			self.__announce = default_bot_cfg["announce"]

	def __get_rand(self, obj):
		"""
			return a random element from a list
		"""		
		r = randint(0, len(obj)-1)
		return obj[r]
		

	def ack(self):
		return self.__get_rand(self.__acks)

	def announce(self):
		return self.__announce

	def greet(self):
		return self.__get_rand(self.__greets)

	def help(self):
		return self.__help

	def nack(self):
		return self.__get_rand(self.__nacks)

class Sleek(ChatBot):

	def __init__(self, api_token, bot_name, DB_path, cfg=None):
		ChatBot.__init__(self, cfg)
		self.slack_client = SlackClient(api_token)
		self.DB_path = DB_path
		backend.init(DB_path)

	def user_join(self, user_id, survey_id):
		"""
			Subscribes user to a survey

			user_id: user id
			survey_id: survey id
		"""
		backend.add_user(self.DB_path, user_id)

	def user_leave(self, user_id, survey_id):
		"""
			Unsubscribes user from survey

			user_id: user id
			survey_id: survey id
		"""
		backend.remove_user(self.DB_path, user_id)

	def schedule(self, user_id, survey_id, am_check=None, pm_check=None):

		"""
			Schedules the survey
			user_id: user id
			survey_id: survey id			
		"""
	 	backend.update_user(self.DB_path, user_id, 
	 						new_am_check=am_check, 
	 						new_pm_check=pm_check)		

	def save_survey(self, user_id, survey_id, timestamp, response):
		"""
			Saves a survey response into the DB
		"""
		backend.save_survey(self.DB_path, user_id, survey_id, timestamp, response)

	def get_survey(self, survey_id):
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

	def connect(self, channel, dbg=False):		
		if self.slack_client.rtm_connect():			
			post = self.greet()
			self.post_channel(channel, post)
			while True:
				resp = self.slack_client.rtm_read()		
				if resp and len(resp) > 0:
					for output in resp:
						if dbg: print "dbg: {}\n".format(repr(output))
						try:							
							text = output['text'].strip().lower()
						   	ts = output['ts']
						   	channel = output['channel']
						   	user = output['user']
						   	#ignore all the messages that do not mention the bot
						   	if self.bot_id not in text: continue
						   	#do stuff here
						   	time.sleep(READ_WEBSOCKET_DELAY)
					   	except KeyError:
					   		pass				
		else:
			raise RuntimeError("Could not connect to RTM API")

	def process(self, text, ts, channel):
		pass
		# if text == "join":

	####
	# Methods to save custom surveys
	####


	# def __retrieve_members(self):
	# 	resp = self.slack_client.api_call("users.list")
	# 	users = {}
	# 	if resp.get('ok'):
	# 		# retrieve all users
	# 		members = resp.get('members')
	# 		for user in members:
	# 			#ignore slackbot
	# 			if 'name' not in user or user.get('id') == "USLACKBOT": continue				
	# 			users[user.get('name')] = user.get('id')							
	# 	else:
	# 		raise RuntimeError("Could not retrieve members list\n{}".format(resp))

	# 	return users

	# def __retrieve_IMs(self):
	# 	resp = self.slack_client.api_call("im.list")
	# 	ims = {}
	# 	if resp.get('ok'):
	# 		for im in resp['ims']:
	# 			if not im['is_user_deleted']:
	# 				ims[im['user']] = im['id']
	# 	else:			
	# 		raise RuntimeError("Could not retrieve IMs list\n{}".format(resp))

	# 	return ims

	
	# def respond(self, post, channel):
	# 	post = post.replace("<@{}>".format(self.bot_id.lower()),"").strip()
	# 	print "[post received: {}]".format(post)
	# 	resp = ChatBot.respond(self, post)
	# 	self.post_channel(channel, resp)

	
	

















# class Sleeker(ChatBot):

# 	def __init__(self, api_token, bot_name, DB_path):
# 		ChatBot.__init__(self)
# 		self.slack_client = SlackClient(api_token)
# 		self.DB_path = DB_path
# 		self.bot_id = None
# 		#maps usernames to ID's
# 		self.users = self.__retrieve_members() 

# 		if bot_name not in self.users:
# 			raise RuntimeError("Could not find bot @{} ID")	
# 		else:			
# 			self.bot_id = self.users[bot_name]
# 			print "[bot_id: #{}]".format(self.bot_id)
# 		self.ims = self.__retrieve_IMs()		

# 	def __load_users(self):		
# 		users = {}
# 		for u in backend.load_users(self.DB_path):
# 			users[u[backend.USER_NAME]]=u[backend.USER_ID]
# 		return users

		
# 	def __retrieve_members(self):
# 		resp = self.slack_client.api_call("users.list")
# 		users = {}
# 		if resp.get('ok'):
# 			# retrieve all users
# 			members = resp.get('members')
# 			for user in members:
# 				#ignore slackbot
# 				if 'name' not in user or user.get('id') == "USLACKBOT": continue				
# 				users[user.get('name')] = user.get('id')							
# 		else:
# 			raise RuntimeError("Could not retrieve members list\n{}".format(resp))

# 		return users

# 	def __retrieve_IMs(self):
# 		resp = self.slack_client.api_call("im.list")
# 		ims = {}
# 		if resp.get('ok'):
# 			for im in resp['ims']:
# 				if not im['is_user_deleted']:
# 					ims[im['user']] = im['id']
# 		else:			
# 			raise RuntimeError("Could not retrieve IMs list\n{}".format(resp))

# 		return ims

# 	def __listen(self, dbg):		
# 		resp = self.slack_client.rtm_read()		
# 		if resp and len(resp) > 0:
# 			for output in resp:
# 				if 'text' in output:
# 					if dbg:
# 						print "dbg: {}\n".format(repr(output))
# 					if self.bot_id in output['text']:					
# 						return output['text'].strip().lower(), \
# 							   output['ts'], \
# 							   output['channel'], \
# 							   output['user']
# 		return None, None, None, None

# 	def respond(self, post, channel):
# 		post = post.replace("<@{}>".format(self.bot_id.lower()),"").strip()
# 		print "[post received: {}]".format(post)
# 		resp = ChatBot.respond(self, post)
# 		self.post_channel(channel, resp)

# 	def post_channel(self, channel, message):
# 		print "[posting:\"{}\" to channel {}]".format(message,channel)
# 		resp = self.slack_client.api_call("chat.postMessage",
#   					 channel=channel,
#   					 as_user=True,
#   					 text=message)
# 		if not resp.get("ok"):
# 			print "\033[31m[error: {}]\033[0m".format(resp["error"])


# 	def post_IM(self, user, message):
# 		im_id = self.ims[self.users[user]]
# 		print "[posting:\"{}\" to user @{} (IM:{})]".format(message,user,im_id)
# 		print self.slack_client.api_call("chat.postMessage",
# 										 channel="{}".format(im_id),
# 										 as_user=True,
# 										 text=message)

# 	def start_chat(self, channel, dbg=False):		
# 		if self.slack_client.rtm_connect():			
# 			post = self.greet()
# 			self.post_channel(channel, post)
# 			while True:
# 				command, ts, channel, user = self.__listen(dbg)
# 				if command is not None:					
# 					self.respond(command, channel)
# 				time.sleep(READ_WEBSOCKET_DELAY)
# 		else:
# 			raise RuntimeError("Could not connect to RTM API")


