from datetime import datetime
import pprint
from slackclient import SlackClient
from string import ascii_letters
import time
import out
#sleek
from sleek import Sleek 

try:	
	from ipdb import set_trace
except ImportError:
	from pdb import set_trace

READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
RECONNECT_WEBSOCKET_DELAY = 60 # 1 minute sleep if reading from firehose fails

class Sleek4Slack():
	
	def __init__(self, confs, init_db=False):				
		if confs["survey_mode"]	== "interactive":
			self.interactive=True
		else:
			self.interactive=False		
		#sleek
		self.sleek = Sleek(confs, init_db=init_db)
		#survey_threads > {thread_id:(user_id, survey_id, response)}
		self.survey_threads = {}
		#these variables will be filled by the connect()
		self.slack_client = None		
		self.bot_name = None
		self.slackers = None 
		self.direct_messages = None
	
	#################################################################
	# CORE METHODS
	#################################################################	

	def connect(self, api_token, bot_name):
		self.bot_name = bot_name
		self.slack_client = SlackClient(api_token)				
		slackers = self.list_slackers()		
		self.sleek.load_users(slackers)
		self.at_bot = "<@{}>".format(slackers[bot_name]).lower() 		
		#open direct messages		
		self.direct_messages = self.list_dms() 			

	def greet_channel(self, channel):
		self.post_slack(channel, self.greet())
		self.post_slack(channel, self.announce("*@{}*".format(self.bot_name)))

	def listen(self, verbose=False, dbg=False):
		"""
			verbose == True, print all the events of type "message"
			dbg     == True, allow unhandled exceptions
		"""
		if not self.slack_client.rtm_connect():					
			raise RuntimeError("Could not connect to RTM API :(")
		
		team_name = self.get_team_name()				
		
		print "[launched @{} > {} | interactive survey: {}]".format(self.bot_name, 
																	team_name,
																	self.interactive)
		while True:		
			reply = None
			try:
				slack_data = self.slack_client.rtm_read()
			except Exception as e:
				print "failed to read: {}".format(e)				
				time.sleep(RECONNECT_WEBSOCKET_DELAY)
				#try to reconnect
				if not self.slack_client.rtm_connect():					
					raise RuntimeError("Could not connect to RTM API :(")
				continue
			for output in slack_data:				
				try:
					msg_type = output["type"]
					if msg_type != "message": continue					
				except KeyError:
					continue				
				if verbose: pprint.pprint(output)
				try:
					text = output['text'].lower() 					
					ts = output['ts']
					channel = output['channel']
				   	user = output['user']		   	
				   	try: 
				   		thread_ts = output['thread_ts']
			   		except KeyError: 
			   			thread_ts = ts				   	
				except KeyError:
					continue			
				context = {"user_id":user, "ts":ts, "channel":channel, "thread_ts":thread_ts}				
			 
				#only react to messages directed at the bot						   	
				if self.at_bot in text or channel in self.direct_messages and 'bot_id' not in output:				
					#remove bot mention
			   		text = text.replace(self.at_bot,"").strip()			   					   		
					#if user is not talking on a direct message with sleek
					#open a new one, and reply there
					if channel not in self.direct_messages:
						new_context = self.greet_user(text, context)						
						context = new_context
						channel = new_context["channel"]
			   		if dbg:
			   			#debug mode lets unhandled exceptions explode
			   			reply = self.sleek.read(text, context)			   			
		   			else:
		   				try:
			   				reply = self.sleek.read(text, context)
		   				except Exception as e:	   					
		   					reply = "```[FATAL ERROR: {}]```".format(e)
		   			#post replies
		   			if type(reply) is list:
		   				for r in reply: self.post_slack(channel, r)
	   				else: self.post_slack(channel, reply)

				print "[waiting for @{}...|{}]".format(self.bot_name, team_name)				
				time.sleep(READ_WEBSOCKET_DELAY)

	def greet_user(self, text, context):
		#open new DM
		user_id = context["user_id"]		
		channel = context["channel"]
		new_dm = self.open_dm(user_id) 
		self.direct_messages[new_dm] = user_id					
		try:
			username = self.sleek.users[user_id].username
		except KeyError:
			username=""
		#greet user and move conversation to a private chat
		self.post_slack(channel, out.GREET_USER.format(self.sleek.greet(), username))		
		#say hi on the new DM		
		self.post_slack(new_dm, "> *you said*: _{}_\n\n".format(text))
		context["channel"] = new_dm

		return context
	
	def get_team_name(self):
		resp = self.slack_client.api_call("team.info") 
		if not resp.get("ok"): 			
			print "\033[31m[error: {}]\033[0m".format(resp["error"])
			return None
		else:
			return resp["team"]["name"]

	def list_dms(self):
		resp = self.slack_client.api_call("im.list")		
		if not resp.get("ok"): 						
			print "\033[31m[error: {}]\033[0m".format(resp["error"])
			return []
		else:
			 dm_ids = {r["id"]:r["user"] for r in resp["ims"] if not r["is_user_deleted"]}
			 return dm_ids

	def list_slackers(self):
		resp = self.slack_client.api_call("users.list")
		users = {}
		if resp.get('ok'):
			# retrieve all users
			members = resp.get('members')
			for user in members:
				if user["deleted"]: continue
				#ignore slackbot
				if 'name' not in user or user.get('id') == "USLACKBOT": continue				
				users[user.get('name')] = user.get('id')							
		else:
			raise RuntimeError("Could not retrieve members list\n{}".format(resp))
		print "*slackers*"
		pprint.pprint(users)
		return users

	def open_dm(self, user):
		resp = self.slack_client.api_call("im.open", user=user)
		if not resp.get("ok"): 			
			print "\033[31m[error: {}]\033[0m".format(resp["error"])
			return None
		else:
			return resp["channel"]["id"]

	def post_slack(self, channel, message, ts=None, attach=None):		
		
		if message is not None and len(message)>0:			
			print u"[posting:\"{}\" to channel {}]".format(message,channel)		
			if ts is not None:
				resp = self.slack_client.api_call("chat.postMessage",
		  					 channel=channel,
		  					 as_user=True,
		  					 thread_ts=ts,
		  					 text=message,
		  					 attachments=attach)
			else:
				resp = self.slack_client.api_call("chat.postMessage",
		  					 channel=channel,
		  					 as_user=True,	  					 
		  					 text=message,
		  					 attachments=attach)
			
			if not resp.get("ok"): print u"\033[31m[error: {}]\033[0m".format(resp["error"])

	