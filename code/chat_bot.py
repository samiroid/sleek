from ipdb import set_trace
from slackclient import SlackClient
import time
from random import randint
import sqlite_backend as backend

READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose

default_bot_cfg={
	"greetings": ["hi","yo","hello :)"],
	"canned_responses": {
		"hello": "hi!",
		"how are you?":"awesome! You?",
		"whats up?":"ah nothing much...u?"
	},
	"questions": ["how are you feeling today?","how did you sleep yesterday?"],
	"excuses":["!?!","I don't understand that :(","sorry, I don't get that"]
}

class ChatBot(object): 
	
	def __init__(self, cfg=None):		

		self.greetings = None
		self.canned_responses = None
		self.questions = None
		self.excuses = None

		if cfg is None:
			print "[starting bot with default confs]"
			self.__load_cfg(default_bot_cfg)
		else:
			print "[loading confs]"
			self.__load_cfg(cfg)

	def __load_cfg(self, cfg):
		
		if "greetings" in cfg:
			self.greetings = cfg["greetings"]
		else:
			self.greetings = default_bot_cfg["greetings"]

		if "canned_responses" in cfg:
			self.canned_responses = cfg["canned_responses"]
		else:
			self.canned_responses = default_bot_cfg["canned_responses"]

		if "questions" in cfg:
			self.questions = cfg["questions"]
		else:
			self.questions = default_bot_cfg["questions"]

		if "excuses" in cfg:
			self.excuses = cfg["excuses"]
		else:
			self.excuses = default_bot_cfg["excuses"]

	def __get_rand(self, obj):
		try:
			r = randint(0, len(obj)-1)
			return obj[r]
		except:
			set_trace()

	def greet(self):
		return self.__get_rand(self.greetings)

	def excuse(self):
		return self.__get_rand(self.excuses)

	def respond(self, question):				
		try:
			return self.canned_responses[question]
		except KeyError:
			return self.excuse()

class Sleek(ChatBot):

	def __init__(self, api_token, bot_name, DB_path):
		ChatBot.__init__(self)
		self.slack_client = SlackClient(api_token)
		self.DB_path = DB_path
		self.bot_id = None
		#maps usernames to ID's
		self.users = self.__retrieve_members() 

		if bot_name not in self.users:
			raise RuntimeError("Could not find bot @{} ID")	
		else:			
			self.bot_id = self.users[bot_name]
			print "[bot_id: #{}]".format(self.bot_id)
		self.ims = self.__retrieve_IMs()		

	def __load_users(self):		
		users = {}
		for u in backend.load_users(self.DB_path):
			users[u[backend.USER_NAME]]=u[backend.USER_ID]
		return users

		
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

	def __listen(self, dbg):		
		resp = self.slack_client.rtm_read()		
		if resp and len(resp) > 0:
			for output in resp:
				if 'text' in output:
					if dbg:
						print "dbg: {}\n".format(repr(output))
					if self.bot_id in output['text']:					
						return output['text'].strip().lower(), \
							   output['ts'], \
							   output['channel'], \
							   output['user']
		return None, None, None, None

	def respond(self, post, channel):
		post = post.replace("<@{}>".format(self.bot_id.lower()),"").strip()
		print "[post received: {}]".format(post)
		resp = ChatBot.respond(self, post)
		self.post_channel(channel, resp)

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

	def start_chat(self, channel, dbg=False):		
		if self.slack_client.rtm_connect():			
			post = self.greet()
			self.post_channel(channel, post)
			while True:
				command, ts, channel, user = self.__listen(dbg)
				if command is not None:					
					self.respond(command, channel)
				time.sleep(READ_WEBSOCKET_DELAY)
		else:
			raise RuntimeError("Could not connect to RTM API")


# class Sleek(ChatBot):

# 	def __init__(self, api_token, bot_name):
# 		ChatBot.__init__(self)
# 		self.slack_client = SlackClient(api_token)
# 		self.bot_id = None
# 		#maps usernames to ID's
# 		self.users = self.__retrieve_members() 

# 		if bot_name not in self.users:
# 			raise RuntimeError("Could not find bot @{} ID")	
# 		else:			
# 			self.bot_id = self.users[bot_name]
# 			print "[bot_id: #{}]".format(self.bot_id)
# 		self.ims = self.__retrieve_IMs()		

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



