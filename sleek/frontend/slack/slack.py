from datetime import datetime
import pprint
from slackclient import SlackClient
from string import ascii_letters
import time
import traceback
#sleek
from ... import Sleek, SleekMsg, out 

import fancyprint as fancier
try:	
	from ipdb import set_trace
except ImportError:
	from pdb import set_trace

READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
RECONNECT_WEBSOCKET_DELAY = 60 # 1 minute sleep if reading from firehose fails

class Sleek4Slack():	
	def __init__(self, confs):				
		self.interactive = confs["survey_mode"] == "interactive"				
		self.bot_name = confs["bot_name"]		
		#these variables will be filled by the connect()
		self.slack_client = None				
		self.DMs = None
		self.user2DM = None
		#sleek
		self.sleek = Sleek(confs, self.remind_user)
		self.open_responses = {}	
	#################################################################
	# CORE METHODS
	#################################################################	
	def connect(self, api_token):
		self.slack_client = SlackClient(api_token)				
		slackers = self.list_slackers()		
		self.sleek.load_users(slackers)
		self.at_bot = "<@{}>".format(slackers[self.bot_name]).lower() 		
		#open direct messages		
		self.DMs = self.list_dms() 			
		#inverse lookup for DMs
		self.user2DM = {v: k for k, v in self.DMs.iteritems()}

	def greet_channel(self, channel):
		self.postMessage(channel, self.sleek.greet())
		bot = "*@{}*".format(self.bot_name)
		self.postMessage(channel, self.sleek.announce(bot))

	def listen(self, verbose=False, dbg=False):
		"""
			verbose == True, print all the events of type "message"
			dbg     == True, allow unhandled exceptions
		"""
		if not self.slack_client.rtm_connect():					
			raise RuntimeError("Could not connect to RTM API :(")		
		team_name = self.get_team_name()				
		status = "[launched {}@{} | interactive: {}]"
		print status.format(self.bot_name, team_name, 
							self.interactive)
		while True:					
			try:
				slack_data = self.slack_client.rtm_read()
			except Exception as e:
				print "failed to read: {}".format(e)				
				time.sleep(RECONNECT_WEBSOCKET_DELAY)
				print "[reconnecting to Slack]"				
				if not self.slack_client.rtm_connect():					
					raise RuntimeError("Could not connect to RTM API :(")
				continue
			for data in slack_data:				
				try:					
					if data["type"] != "message": continue					
				except KeyError:
					continue				
				if verbose: pprint.pprint(data)
				try:
					text    = data['text'].lower()						
					ts      = data['ts']
					channel = data['channel']
				   	user    = data['user']		   					   	
				except KeyError:
					continue			
				context = {"user_id":user, "ts":ts, 
				   		   "channel":channel}		
				reply=None			
		 		if 'bot_id' in data and text == "pong":			 		
					#this message was posted by pong (as a bot)
					#thus, changing back to user reponding to survey			 		
			 		self.run_interactive_survey(data) 		
				#only react to messages directed at the bot
				elif self.at_bot in text or channel in self.DMs \
				 and 'bot_id' not in data:
				 	#if this is an interactive survey read survey 'notes'
				 	if self.interactive and user in self.sleek.ongoing_surveys:
				 		ongoing_survey = self.sleek.ongoing_surveys[user]
				 		if ongoing_survey.has_open_notes():	
				 			
							ongoing_survey.put_notes(text)
							rep = self.sleek.get_survey_answers(user)
							#update current answer post  				
							# _, ans_thread, notes_thread = self.open_responses[user]
							ans_thread = self.open_responses[user]["answer_thread"]
							notes_thread = self.open_responses[user]["notes_thread"]
							self.updateMessage(channel,
									  			rep,
												ans_thread)							
	 						self.updateMessage(channel, out.NOTE_CONFIRM_2,
		 							notes_thread)
						continue
					#remove bot mention
			   		text = text.replace(self.at_bot,"").strip()
					#if user is not on DM with sleek 
					#open a new one, and reply there
					if channel not in self.DMs:
						new_context = self.greet_user(text, context)
						context = new_context
						channel = new_context["channel"]
	   				try:
		   				reply = self.sleek.read(text, context)
	   				except Exception as e:
	   					#debug mode lets unhandled exceptions explode
	   					if dbg:
	   						traceback.print_exc()
	   						raise e
   						else: reply = ["```[FATAL ERROR]```"]
		   			if reply is not None:
			   			assert type(reply) is list, set_trace()
			   			#post replies			   			
			   			for r in reply: self.postMessage(channel, r)
   					
				print "[waiting for {}@{}...]".format(self.bot_name, team_name)	
				time.sleep(READ_WEBSOCKET_DELAY)

	def run_interactive_survey(self, data):
		user_id   = data["attachments"][0]["author_name"]
		thread_ts = data["thread_ts"]
		text      = data["attachments"][0]["text"]
		channel   = self.user2DM[user_id]
		try:
			this_survey = self.sleek.ongoing_surveys[user_id]
		except KeyError: #there is no survey going for this user				
				return
 		arg1, arg2 = text.split()	 		
 		if arg2 == "[sleek:ok]":
 			# survey_thread, answer_thread, notes_thread = self.open_responses[user_id]
 			survey_thread = self.open_responses[user_id]["survey_thread"]
 			answer_thread = self.open_responses[user_id]["answer_thread"]
 			notes_thread  = self.open_responses[user_id]["notes_thread"]
 			del self.open_responses[user_id]
 			#delete answers 				
			self.deleteMessage(channel, notes_thread)			
			self.deleteMessage(channel, survey_thread)
			# self.deleteMessage(channel, answer_thread)
 			try:
 				self.sleek.ongoing_surveys[user_id].save()
 				self.updateMessage(channel, 
							    out.ANSWERS_SAVE_OK,
							    answer_thread)
 			except RuntimeError as e:
 				#replace survey with message
 				self.postMessage(channel, 
								e.message)
		elif arg2 == "[sleek:cancel]":
 			self.sleek.cancel_survey(user_id)
 			#update UI
 			try: #there are already some answers 				
 				# survey_thread, ans_thread, notes_thread = self.open_responses[user_id]
 				survey_thread = self.open_responses[user_id]["survey_thread"]
 				answer_thread = self.open_responses[user_id]["answer_thread"]
 				notes_thread  = self.open_responses[user_id]["notes_thread"]
				del self.open_responses[user_id]
				#delete answers 				 				
				if notes_thread is not None:
 					self.deleteMessage(channel, notes_thread)
				self.deleteMessage(channel, answer_thread)
			except KeyError: 
				survey_thread = thread_ts
			self.deleteMessage(channel, survey_thread)
			self.postMessage(channel, 
		 				    out.SURVEY_CANCELED)
		elif arg2 == "[sleek:notes]":
			# survey_thread, answer_thread, _ = self.open_responses[user_id]
			survey_thread = self.open_responses[user_id]["survey_thread"]
 			answer_thread = self.open_responses[user_id]["answer_thread"]
 			
			if not self.sleek.ongoing_surveys[user_id].has_open_notes():
 				self.sleek.ongoing_surveys[user_id].put_notes("")
 				resp = self.postMessage(channel, 
 									  out.ANSWERS_ADD_NOTE, 
 									  thread_ts=answer_thread)
 				print "Channel: " + resp["channel"]
 				#keep the post id for the notes
 				# self.open_responses[user_id][2] = ts
 				self.open_responses[user_id]["notes_thread"] = resp["ts"]
 				
 		else: #this an answer 			
	 		q_id, ans = arg1, arg2
	 		this_survey.put_answer(q_id, int(ans))
			rep = self.sleek.get_survey_answers(user_id)
			try: #update current answer post  				
				# survey_thread, answer_thread, _ = self.open_responses[user_id]
				survey_thread = self.open_responses[user_id]["survey_thread"]
 				answer_thread = self.open_responses[user_id]["answer_thread"]
				self.updateMessage(channel, 
									  rep, 
									  answer_thread)				
			except KeyError: #new answer				
	 			resp = self.postMessage(channel, rep)
	 			ts = resp["ts"]
	 			#holds the ids to the survey, answer and notes post
	 			# self.open_responses[user_id]=[thread_ts, ts, None]
	 			self.open_responses[user_id]={"survey_thread":thread_ts, 
	 										  "answer_thread":ts, 
	 										  "notes_thread":None,
	 										  "notes_dm":None}
	 			survey_thread = thread_ts
 			#if survey is complete show additional buttons
			if self.sleek.ongoing_surveys[user_id].is_complete():
				survey_msg = this_survey.get_SleekMsg()				
				survey_msg.set_field("ok_button", True)
				survey_msg.set_field("notes_button", True)
				self.updateMessage(channel, 
									  survey_msg, 
									  survey_thread)

	def greet_user(self, text, context):
		#open new DM
		user_id = context["user_id"]		
		channel = context["channel"]
		new_dm = self.open_dm(user_id) 
		self.DMs[new_dm] = user_id					
		try:
			username = self.sleek.users[user_id].username
		except KeyError:
			username=""
		#greet user and move conversation to a private chat
		self.postMessage(channel, out.GREET_USER.format(self.sleek.greet(), username))		
		#say hi on the new DM	
		hello = u"Hello! I prefer talking in private :slightly_smiling_face:"	
		self.postMessage(new_dm, hello)
		self.postMessage(new_dm, u"> *you said*: _{}_\n\n".format(text))
		context["channel"] = new_dm

		return context
	
	def remind_user(self, user_id, survey_id, period):
		self.postMessage(user_id, out.REMIND_SURVEY.format(survey_id,period))

	#################################################################
	# SLACK API METHODS
	#################################################################	

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

	def postMessage(self, channel, message, thread_ts=None, attach=None):		
			
		if type(message) == unicode:
			resp = self.__post(channel, message, thread_ts, attach)
		elif type(message) == SleekMsg:
			message.set_field("interactive", self.interactive)		
			if message.get_field("user_id") is not None:
				message.set_field("api_token", self.slack_client.token)
			fm = fancier.format(message)		
			if type(fm) == unicode:
				resp = self.__post(channel, fm, thread_ts=thread_ts)
			elif type(fm) == list: #attachments are lists of dicts
				resp = self.__post(channel, message=" ", 
									  thread_ts=thread_ts, attach=fm)
			else:
				raise NotImplementedError			
		else:
			raise NotImplementedError

		return resp

	def __post(self, channel, message, thread_ts=None, attach=None):		
		
		if message is not None and len(message)>0:			
			print u"[posting:\"{}\" to channel {}]".format(message,channel)		
			if thread_ts is not None:
				resp = self.slack_client.api_call("chat.postMessage",
		  					 channel=channel,
		  					 as_user=True,
		  					 thread_ts=thread_ts,
		  					 text=message,
		  					 attachments=attach)
			else:
				resp = self.slack_client.api_call("chat.postMessage",
		  					 channel=channel,
		  					 as_user=True,	  					 
		  					 text=message,
		  					 attachments=attach)			
			if not resp.get("ok"): 
				print u"\033[31m[error: {}]\033[0m".format(resp["error"])
				return None
			else:
				return resp

	def updateMessage(self, channel, message, ts, attach=None):
		
		if type(message) == unicode:
			resp = self.__update(channel, message, ts, attach)
		elif type(message) == SleekMsg:
			message.set_field("interactive", self.interactive)		
			if message.get_field("user_id") is not None:
				message.set_field("api_token", self.slack_client.token)
			fm = fancier.format(message)		
			if type(fm) == unicode:
				resp = self.__update(channel, fm, ts=ts)
			elif type(fm) == list: #attachments are lists of dicts
				resp = self.__update(channel, message=" ", 
									  ts=ts, attach=fm)
			else:
				raise NotImplementedError			
		else:
			raise NotImplementedError

		return resp

	def __update(self, channel, message, ts, attach=None):		
		
		if message is not None and len(message)>0:			
			print u"[updating post:{} -> \"{}\" @ channel {}]".format(ts, message,channel)					
			resp = self.slack_client.api_call("chat.update",
	  					 channel=channel,
	  					 as_user=True,
	  					 ts=ts,
	  					 text=message,
	  					 attachments=attach)
			if not resp.get("ok"): 
				print u"\033[31m[error: {}]\033[0m".format(resp["error"])
				return None
			else:
				return resp

	def deleteMessage(self, channel, ts):						
		resp = self.slack_client.api_call("chat.delete",
  					 channel=channel,
  					 as_user=True,
  					 ts=ts)
		if not resp.get("ok"): 
			print u"\033[31m[error: {}]\033[0m".format(resp["error"])
			return None
		else:
			return resp
	