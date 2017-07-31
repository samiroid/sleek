from apscheduler.schedulers.background import BackgroundScheduler
from collections import defaultdict
from datetime import datetime
import json
import pprint
from slackclient import SlackClient
from slack_utils import list_slackers, open_dm, get_team_name, list_dms, post_slack
from string import ascii_letters
import time

#sleek
from backend import LocalBackend as Backend
import display
import out
from _sleek import Sleek

try:	
	from ipdb import set_trace
except ImportError:
	from pdb import set_trace

READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
RECONNECT_WEBSOCKET_DELAY = 60 # 1 minute sleep if reading from firehose fails

class Sleek4Slack(Sleek):
	sleek_announce = ''' I am {}, the chat bot :robot_face: -- If we never met, you can start by typing `help` '''	
	
	help_dict={
		"delete": "`delete` `<SURVEY_ID>` | `all` : delete all the answers to survey `<SURVEY_ID>` (or all)",
		"join": "`join` `<SURVEY_ID>` `[HH:MM (AM|PM)]`: join survey `<SURVEY_ID>` and (optionally) set reminders: e.g., _join stress 9:00AM 2:00PM_", 
		"leave":"`leave` `<SURVEY_ID>`: leave survey `<SURVEY_ID>`",
		"list":"`list`: see a list of surveys",
		"report":"`report` `<SURVEY_ID>`: see previous answers to survey `<SURVEY_ID>`",
		"notes":"`notes` `<SURVEY_ID>`: see previous notes added to survey `<SURVEY_ID>`",
		"survey":"`survey` `<SURVEY_ID>`: answer to survey `<SURVEY_ID>`",
		"reminder":"`reminder` `<SURVEY_ID>` `HH:MM (AM|PM)`: set reminders for survey `<SURVEY_ID>`",
		"reminder remove":"`reminder remove` `<SURVEY_ID>`: remove reminders for survey `<SURVEY_ID>`",
		}
	
	sleek_help = '''  This a list of the commands I understand:				      

>>> 
- `delete` `<SURVEY_ID>` | `all` : delete all the answers to survey `<SURVEY_ID>` (or all)
- `join` `<SURVEY_ID>` `[HH:MM (AM|PM)]`: join survey `<SURVEY_ID>` and (optionally) set reminders: e.g., _join stress 9:00AM 2:00PM_ 
- `leave` `<SURVEY_ID>`: leave survey `<SURVEY_ID>`
- `list`: see a list of surveys
- `report` `<SURVEY_ID>`: see previous answers to survey `<SURVEY_ID>`
- `notes` `<SURVEY_ID>`: see previous notes added to survey `<SURVEY_ID>`
- `survey` `<SURVEY_ID>`: answer to survey `<SURVEY_ID>`
- `reminder` `<SURVEY_ID>` `HH:MM (AM|PM)`: set reminders for survey `<SURVEY_ID>`
- `reminder remove` `<SURVEY_ID>`: remove reminders for survey `<SURVEY_ID>`
'''

	default_cfg={
				"announce": sleek_announce,				
				"help": sleek_help				
				}

	def __init__(self, db, cfg=default_cfg):
		assert isinstance(db, Backend)
		self.backend = db
		Sleek.__init__(self, cfg)		
		#{survey_id:survey}
		self.current_surveys = {x[0]:json.loads(x[1]) for x in self.backend.list_surveys()}						
		#reminders > {(user_id, survey_id):{"am":reminder_am, "pm":reminder_pm}}		
		self.reminders = defaultdict(dict)				
		#survey_threads > {thread_id:(user_id, survey_id, response)}
		self.survey_threads = {}
		#these variables will be filled by the connect()
		self.slack_client = None		
		self.bot_name = None
		self.interactive = False
	
	#################################################################
	# CORE METHODS
	#################################################################	

	def connect(self, api_token, bot_name):
		self.slack_client = SlackClient(api_token)				
		self.slackers = list_slackers(self.slack_client)
		self.id2user  = {uid:uname for uname, uid in self.slackers.items()}		
		self.bot_name = bot_name		
		#open direct messages		
		self.direct_messages = list_dms(self.slack_client) 		

	def get_surveys(self, user_id):
		us = self.backend.list_surveys(user_id)		
		user_surveys  = {x[1]:None for x in us}				
		surveys = {s:True if s in user_surveys else False for s in self.current_surveys.keys()}				
		return surveys		

	def greet_channel(self, channel):
		post_slack(self.slack_client, channel, self.greet())
		post_slack(self.slack_client, channel, self.announce("*@{}*".format(self.bot_name)))

	def listen(self, interactive=False, verbose=False, dbg=False):
		"""
			verbose == True, print all the events of type "message"
			dbg == True, allow unhandled exceptions
		"""
		if not self.slack_client.rtm_connect():					
			raise RuntimeError("Could not connect to RTM API :(")
		#reminder scheduler
		self.scheduler = BackgroundScheduler()
		self.scheduler.start()
		self.load_reminders()	
		team_name = get_team_name(self.slack_client)		
		self.interactive = interactive
		hat_bot = "<@{}>".format(self.slackers[self.bot_name]).lower() 		
		print "[launched @{} > {} | interactive survey: {}]".format(self.bot_name, team_name, self.interactive)
		while True:		
			reply = None
			try:
				slack_data = self.slack_client.rtm_read()									
			except Exception as e:
				print "failed to read"
				print e
				time.sleep(RECONNECT_WEBSOCKET_DELAY)
				continue
			for output in slack_data:				
				if verbose and output["type"] == "message": 
					pprint.pprint(output)
				if output["type"] != "message": continue								
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
			   	#only react to ongoing survey threads 
				if thread_ts in self.survey_threads:
					if 'bot_id' in output:
						if text != "pong":
							continue   	
						else:
							user, survey, channel, response = self.survey_threads[thread_ts]
							context["user_id"] = user
							context["channel"] = channel							
							text = output["attachments"][0]["text"]							
					#remove bot mention
					pprint.pprint(output)
   					text = text.replace(hat_bot,"").strip()			
   					if self.interactive:
   						self.interactive_survey(text, context)
					else:   							
			   			self.run_survey(text, context)	   			
				#or messages directed at the bot						   	
				elif hat_bot in text or channel in self.direct_messages and 'bot_id' not in output:					
					#remove bot mention
			   		text = text.replace(hat_bot,"").strip()			   					   		
					#if user is not talking on a direct message with sleek
					#open a new one, and reply there
					if channel not in self.direct_messages:												
						new_context = self.greet_user(text, context)						
						context = new_context
			   		if dbg:
			   			#debug mode lets unhandled exceptions explode
			   			self.process(text, context)			   			
		   			else:
		   				try:
			   				self.process(text, context)
		   				except Exception as e:	   					
		   					reply = "```[FATAL ERROR: {}]```".format(e)
		   					post_slack(self.slack_client, channel, reply, thread_ts)

				print "[waiting for @{}...|{}]".format(self.bot_name, team_name)				
				time.sleep(READ_WEBSOCKET_DELAY)

	def remind_user(self, user_id, survey_id, period):
		post_slack(self.slack_client, user_id, out.REMIND_SURVEY.format(survey_id,period))				
		
	def load_reminders(self):
		data = self.backend.get_reminders()
		#user_id, survey_id, am_check, pm_check
		print "[loading reminders]"
		for user_id, survey_id, am, pm in data:						 
			if am is not None: 
				am_schedule = datetime.strptime(am , '%I:%M%p').time()				
				self.__schedule_reminder(user_id, survey_id, am_schedule)				
			if pm is not None: 
				pm_schedule = datetime.strptime(pm , '%I:%M%p').time()
				self.__schedule_reminder(user_id, survey_id, pm_schedule)				

	#################################################################
	# BOT COMMAND METHODS
	#################################################################	
	
	def cmd_delete(self, tokens, context):
		channel = context["channel"]	
		thread_ts = context["thread_ts"]	
		if len(tokens) < 2: 			
			post_slack(self.slack_client, channel, out.MISSING_PARAMS, ts=thread_ts) 
		else:
			user_id = context["user_id"]				
			survey_id = tokens[1]	
			#check if user can delete answers to this survey
			#if ok err_msg will be empty
			error = self.__is_valid_survey(user_id, survey_id)
			if len(error) == 0: 
				if not self.backend.delete_answers(user_id, survey_id):
					error = out.ANSWERS_DELETE_FAIL.format(survey_id.upper())
			if len(error) == 0: 
				txt = out.ANSWERS_DELETE_OK.format(survey_id.upper())
				post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)			
				post_slack(self.slack_client, channel, txt, ts=thread_ts)
			else:
				post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)			
				post_slack(self.slack_client, channel, error, ts=thread_ts)

	def cmd_join(self, tokens, context):
		channel = context["channel"]	
		thread_ts = context["thread_ts"]	
		if len(tokens) < 2: 			
			post_slack(self.slack_client, channel, out.MISSING_PARAMS, ts=thread_ts) 
		else:
			user_id = context["user_id"]						
			survey_id = tokens[1]
			error = ""
			#check if survey exists
			if not survey_id in self.current_surveys: 
				error = out.SURVEY_UNKNOWN.format(survey_id.upper())
			#check if user already subscrided this survey
			if len(error) == 0:			
				try:
					if self.get_surveys(user_id)[survey_id]:
						error = out.SURVEY_IS_SUBSCRIBED.format(survey_id.upper())
				except KeyError: 
					pass		
			#all the reminder schedules have to be valid
			if len(error) == 0:					
				for t in tokens[2:]:
					try: 
						_ = self.__get_time(t)				
					except RuntimeError as e:
						error = str(e)
			#try to join survey					
			if len(error) == 0:					
				try:			
					if not self.backend.join_survey(user_id, survey_id):
						error = out.SURVEY_JOIN_FAIL.format(survey_id.upper())
				except RuntimeError as e:			
					error = out.SURVEY_JOIN_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))		
			#success!
			if len(error) == 0:	
				post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)				
				post_slack(self.slack_client, channel, out.SURVEY_JOIN_OK.format(survey_id.upper()), ts=thread_ts)	
				if len(tokens)>2:
					resp = self.cmd_reminder(tokens, context, post=False)
					post_slack(self.slack_client, channel, resp, ts=thread_ts)		
			else:
				#oops
				post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)			
				post_slack(self.slack_client, channel, error, ts=thread_ts)
	
	def cmd_leave(self, tokens, context):
		channel = context["channel"]	
		thread_ts = context["thread_ts"]	
		if len(tokens) < 2: 			
			post_slack(self.slack_client, channel, out.MISSING_PARAMS, ts=thread_ts) 
		else:		
			user_id = context["user_id"]
			survey_id = tokens[1]		
			#check if user can leave survey			
			error = self.__is_valid_survey(user_id, survey_id)
			if len(error) == 0: 
				if not self.backend.leave_survey(user_id, survey_id):
					error = out.SURVEY_LEAVE_FAIL.format(survey_id.upper())									
			#remove reminder triggers			
			self.__schedule_reminder(user_id, survey_id, None)			
			if len(error) == 0:	
				post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)				
				post_slack(self.slack_client, channel, out.SURVEY_LEAVE_OK.format(survey_id.upper()), ts=thread_ts)	
			else:
				post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)			
				post_slack(self.slack_client, channel, error, ts=thread_ts)
			
	def cmd_list(self, tokens, context):
		user_id = context["user_id"]
		channel = context["channel"]	
		thread_ts = context["thread_ts"]	
		us = self.backend.list_surveys(user_id)		
		user_surveys  = {x[1]:(x[2],x[3]) for x in us}
		other_surveys = [s for s in self.current_surveys.keys() if s not in user_surveys]	
		# display.survey_list(user_surveys,other_surveys)		
		survey_list = display.attach_survey_list(user_surveys,other_surveys)
		post_slack(self.slack_client, channel, self.ack(), ts=thread_ts, attach=survey_list)

	def cmd_report(self, tokens, context):
		channel = context["channel"]	
		thread_ts = context["thread_ts"]	
		if len(tokens) < 2: 
			post_slack(self.slack_client, channel, out.MISSING_PARAMS, ts=thread_ts) 
		else:
			user_id = context["user_id"]
			survey_id = tokens[1]
			#if ok err_msg will be empty
			error = self.__is_valid_survey(user_id, survey_id)
			if len(error) == 0:
				try:
					rep = self.backend.get_report(user_id, survey_id)
					if len(rep) == 0:
						error = out.REPORT_EMPTY.format(survey_id.upper())
				except RuntimeError as e:
					error = out.REPORT_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))
			if len(error) == 0:
				notez = self.backend.get_notes(user_id, survey_id)
				report_attach = display.attach_report(self.current_surveys[survey_id], rep, notez)
				post_slack(self.slack_client, channel, self.ack(),ts=thread_ts)
				post_slack(self.slack_client, channel, "", attach=report_attach,ts=thread_ts)
			else:
				post_slack(self.slack_client, channel, self.oops(),ts=thread_ts)
				post_slack(self.slack_client, channel, error,ts=thread_ts)
				
	def cmd_reminder(self, tokens, context, post=True):
		channel = context["channel"]	
		thread_ts = context["thread_ts"]	
		if len(tokens) < 3: 			
			post_slack(self.slack_client, channel, out.MISSING_PARAMS, ts=thread_ts) 
		else:				
			user_id = context["user_id"]				
			survey_id = tokens[1]
			#check if user can add reminder to this survey			
			error = self.__is_valid_survey(user_id, survey_id)
			if len(error) == 0: 					
				#collect new schedules
				am_schedule,pm_schedule = None, None
				try:
					for t in tokens[1:]:					
						if   "am" in t:	am_schedule = self.__get_time(t)
						elif "pm" in t: pm_schedule = self.__get_time(t)						
				except RuntimeError as e:
					error = str(e)			
			#set reminders
			if len(error) == 0:				
				for reminder in [am_schedule,pm_schedule]:	
					if reminder is not None: 
						#save new reminder schedule
						if not self.backend.set_reminder(user_id, survey_id, reminder.strftime('%I:%M%p')):
							error += out.REMINDER_FAIL.format(survey_id) + " [failed to update the DB]\n"
						else:
							#set new reminder trigger
							self.__schedule_reminder(user_id, survey_id, reminder)					
			#success!
			if len(error) == 0:				
				#choose a return message
				if am_schedule is not None and pm_schedule is not None:
					am = am_schedule.strftime('%I:%M%p')
					pm = pm_schedule.strftime('%I:%M%p')
					txt = out.REMINDER_OK_2.format(survey_id.upper(), am, pm)					
				elif am_schedule is not None:			
					am = am_schedule.strftime('%I:%M%p')		
					txt = out.REMINDER_OK.format(survey_id.upper(), am)
				elif pm_schedule is not None:				
					pm = pm_schedule.strftime('%I:%M%p')
					txt = out.REMINDER_OK.format(survey_id.upper(), pm)
				else:
					txt = out.REMINDER_FAIL.format(survey_id)
				if post:
					post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)
					post_slack(self.slack_client, channel, txt, ts=thread_ts)
				else:
					return txt
			else:	
				post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)			
				post_slack(self.slack_client, channel, error, ts=thread_ts)
			
	def cmd_remove_reminder(self, tokens, context):
		channel = context["channel"]	
		thread_ts = context["thread_ts"]	
		if len(tokens) < 2: 			
			post_slack(self.slack_client, channel, out.MISSING_PARAMS, ts=thread_ts) 
		else:				
			user_id = context["user_id"]				
			survey_id = tokens[1]
			#check if user can add reminder to this survey			
			error = self.__is_valid_survey(user_id, survey_id)
			if len(error) == 0: 					
				#remove reminder schedule 
				if not self.backend.set_reminder(user_id, survey_id, None):
					error = out.REMINDER_FAIL.format(survey_id) + " [failed to update the DB]\n"		
			if len(error) == 0:
				#remove reminder triggers
				self.__schedule_reminder(user_id, survey_id, None)			
				post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)			
				post_slack(self.slack_client, channel, out.REMINDER_REMOVE_OK.format(survey_id.upper()), ts=thread_ts)				
			else:
				post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)			
				post_slack(self.slack_client, channel, error, ts=thread_ts)		

	def cmd_survey(self, tokens, context):
		user_id = context["user_id"]		
		channel = context["channel"]	
		thread_ts = context["thread_ts"]	
		if len(tokens) < 2: 			
			post_slack(self.slack_client, channel, out.MISSING_PARAMS, ts=thread_ts) 
		else:
			survey_id = tokens[1]
			#check if user can open this survey
			#if ok err_msg will be empty
			error = self.__is_valid_survey(user_id, survey_id)
			if len(error) == 0: 			
				#register this thread as an open survey
				self.survey_threads[context["thread_ts"]] = (user_id, survey_id, channel,  None)
				s = self.current_surveys[survey_id]		
				post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)			
				if self.interactive:
					attach = display.attach_survey(s)
					post_slack(self.slack_client, channel, "", ts=thread_ts, attach=attach)							
				else:
					survey = display.survey(s)
					post_slack(self.slack_client, channel, survey, ts=thread_ts)							
			else:
				post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)			
				post_slack(self.slack_client, channel, error, ts=thread_ts)		
	
	def greet_user(self, text, context):
		#open new DM
		user = context["user_id"]		
		channel = context["channel"]
		new_dm = open_dm(self.slack_client, user) 
		self.direct_messages[new_dm] = user					
		try:
			username = self.id2user[user]
		except KeyError:
			username=""
		#greet user and move conversation to a private chat
		post_slack(self.slack_client, channel, out.GREET_USER.format(self.greet(), username))		
		#say hi on the new DM		
		post_slack(self.slack_client, new_dm, "> *you said*: _{}_\n\n".format(text))
		context["channel"] = new_dm
		context["thread_ts"] = None
		
		return context
	
	#################################################################
	#  INTERACTIONS
	#################################################################

	def process(self, text, context):
		user_id = context["user_id"]		
		tokens = text.split()
		action = tokens[0]
		params =  u','.join(tokens[1:])		
		print u"[user: {}| action: {}({})]".format(user_id, action, params)								
		#Actions
		# ---- DELETE DATA ----
		if action == "delete": self.cmd_delete(tokens, context)						
		
		# ---- JOIN SURVEY ----
		elif action == "join": self.cmd_join(tokens, context)
			
		# ---- LEAVE SURVEY ----
		elif action == "leave":	self.cmd_leave(tokens, context)											
			
		# ---- LIST SURVEYS ----
		elif action == "list": self.cmd_list(tokens, context)	

		# ---- SHOW REPORT ----
		elif action == "report": self.cmd_report(tokens, context)		
		
		# ---- SCHEDULE SURVEY ----
		elif action == "reminder": 
			if "remove" in tokens:
				self.cmd_remove_reminder(tokens, context)			
			else:
				self.cmd_reminder(tokens, context)			

		# ---- ANSWER SURVEY ----
		elif action == "survey": self.cmd_survey(tokens, context)
					
		# ---- PASS IT TO THE PARENT CLASS (maybe it knows how to handle this input)
		else:
			thread_ts = context["thread_ts"]
			channel = context["channel"]
			replies = Sleek.chat(self, tokens, context)		
			for r in replies: post_slack(self.slack_client, channel, r, ts=thread_ts) 

	def run_survey(self, text, context):
   		tokens = text.split()
   		channel = context["channel"]
   		thread_ts = context["thread_ts"]
   		error = ""
		if tokens[0] == "cancel":
			#remove current thread from open survey threads
			del self.survey_threads[thread_ts]			
			post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)
			post_slack(self.slack_client, channel, out.SURVEY_CANCELED, ts=thread_ts)
		elif tokens[0] == "ok":
			open_user, open_survey, open_channel, response = self.survey_threads[thread_ts] 			
			if response is None: 
				post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)
				post_slack(self.slack_client, channel, out.ANSWERS_INVALID, ts=thread_ts)
			else:
				response = self.__answers_2_indices(open_survey, response)
				ts = datetime.now().strftime('%Y-%m-%d %H:%M')				
				response["ts"]=ts
				if not self.backend.save_answer(open_user, open_survey, response):			
					post_slack(self.slack_client, channel, out.ANSWERS_SAVE_FAIL, ts=thread_ts)
				else:
					#if saved ok, remove this survey from the open threads
					del self.survey_threads[thread_ts]
					post_slack(self.slack_client, channel, out.ANSWERS_SAVE_OK, ts=thread_ts)
		elif tokens[0] == "notes":
			open_user, open_survey, open_channel, response = self.survey_threads[thread_ts] 
			#add a placeholder for the notes on the response
			response["notes"]=""
			self.survey_threads[thread_ts] = (open_user, open_survey, channel, response)
			post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)
			post_slack(self.slack_client, channel, out.ANSWERS_ADD_NOTE, ts=thread_ts)						
		else:
			#parse the answer			
			open_user, open_survey, open_channel, open_response = self.survey_threads[thread_ts]					
			#case where the user already answered the questions and 
			#is adding a note
			if open_response is not None and "notes" in open_response:
				response = open_response
				response["notes"] = text				
			else:
				#otherwise these should be answers to the survey
				questions = self.current_surveys[open_survey]["questions"]		
				#assumes responses are separated by white spaces		
				try:
					#answers are indices into a list of choices
					answers = [ascii_letters.index(a) for a in text.split()]
				except ValueError:
					error = out.ANSWERS_INVALID
				if len(error) == 0:
					#incorrect number of answers
					if len(answers) > len(questions):
						error = out.ANSWERS_TOO_MANY.format(len(questions), len(answers))
					elif len(answers) < len(questions):
						error = out.ANSWERS_TOO_FEW.format(len(questions), len(answers))				
				if len(error) == 0:
					#response dictionary
					response = {}
					for q, a in zip(questions, answers):
						q_id = q["q_id"]
						choices = q["choices"]
						if a not in range(len(choices)):
							error = out.ANSWERS_BAD_CHOICE.format(q["q_id"])
							break
						else:
							response[q_id] = choices[a]		
			if len(error) == 0:
				#cache this response
				self.survey_threads[thread_ts] = (open_user, open_survey, open_channel, response)		
				attach = display.attach_answer(response, open_survey, cancel_button=False)		
				post_slack(self.slack_client, channel, "", ts=thread_ts, attach=attach)
				post_slack(self.slack_client, channel, out.ANSWERS_CONFIRM, ts=thread_ts)					
			else:
				post_slack(self.slack_client, channel, error, ts=thread_ts)

	def interactive_survey(self, text, context):
   		tokens = text.split()
   		channel = context["channel"]
   		thread_ts = context["thread_ts"]
   		error = ""
		if tokens[0] == "cancel":
			#remove current thread from open survey threads
			del self.survey_threads[thread_ts]			
			post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)
			post_slack(self.slack_client, channel, out.SURVEY_CANCELED, ts=thread_ts)
		elif tokens[0] == "ok":
			open_user, open_survey, open_channel, response = self.survey_threads[thread_ts] 			
			if response is None: 
				post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)
				post_slack(self.slack_client, channel, out.ANSWERS_INVALID, ts=thread_ts)
			else:
				response = self.__answers_2_indices(open_survey, response)
				#record timestamp
				ts = datetime.now().strftime('%Y-%m-%d %H:%M')
				response["ts"]=ts
				if not self.backend.save_answer(open_user, open_survey, response):			
					post_slack(self.slack_client, channel, out.ANSWERS_SAVE_FAIL, ts=thread_ts)
				else:
					#if saved ok, remove this survey from the open threads
					del self.survey_threads[thread_ts]
					post_slack(self.slack_client, channel, out.ANSWERS_SAVE_OK, ts=thread_ts)
		elif tokens[0] == "notes":
			open_user, open_survey, open_channel, response = self.survey_threads[thread_ts] 
			#add a placeholder for the notes on the response
			response["notes"]=""
			self.survey_threads[thread_ts] = (open_user, open_survey, open_channel, response)
			post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)
			post_slack(self.slack_client, channel, out.ANSWERS_ADD_NOTE, ts=thread_ts)						
		else:
			#parse the answer						
			open_user, open_survey, open_channel, open_response = self.survey_threads[thread_ts]		
			questions = self.current_surveys[open_survey]["questions"]		
			#case where the user already answered the questions and 
			#is adding a note
			if open_response is not None and "notes" in open_response:
				response = open_response
				response["notes"] = text				
			else:
				#otherwise these should be answers to the survey
				if open_response is not None:
					#continue
					response = open_response
				else:
					#this is a brand new answer
					response = {}				
				tokens = text.split()			
				if len(tokens) != 2:
					error = out.ANSWERS_INVALID
				if len(error) == 0 :
					q_index, answer = tokens
					try:
						q_index = int(q_index)
						answer = int(answer)
					except ValueError:
						error = out.ANSWERS_INVALID
					if q_index < 0 or \
					   q_index > len(questions)-1 or \
					   answer < 0:
						error = out.ANSWERS_INVALID					
				if len(error) == 0 :
					question = questions[q_index-1]
					q_id = question["q_id"]
					choices = question["choices"]					
					if answer not in range(len(choices)):
						error = out.ANSWERS_BAD_CHOICE.format(q_id)
					else:
						response[q_id] = choices[answer]												
			if len(error) == 0:
				#cache this response
				self.survey_threads[thread_ts] = (open_user, open_survey, open_channel, response)		
				#repost the survey
				survey = self.current_surveys[open_survey]		
				attach_survey = display.attach_survey(survey)
				post_slack(self.slack_client, channel, "", ts=thread_ts, attach=attach_survey)							
				#post the current answers
				#if the survey is all filled ask to confirm
				if len(response) == len(questions):
					answer_attach = display.attach_answer(response, open_survey, ok_button=True, notes_button=True)	
					post_slack(self.slack_client, channel, "", ts=thread_ts, attach=answer_attach)
					post_slack(self.slack_client, channel, out.ANSWERS_CONFIRM, ts=thread_ts)
				elif len(response) >= len(questions) and "notes" in response:
					answer_attach = display.attach_answer(response, open_survey, ok_button=True)		
					post_slack(self.slack_client, channel, "", ts=thread_ts, attach=answer_attach)
					post_slack(self.slack_client, channel, out.NOTE_CONFIRM, ts=thread_ts)
				else:
					attach = display.attach_answer(response, open_survey)		
					post_slack(self.slack_client, channel, "", ts=thread_ts, attach=attach)
			else:
				post_slack(self.slack_client, channel, error, ts=thread_ts)
   		
	#################################################################
	# AUX METHODS
	#################################################################		

	def __is_valid_survey(self, user_id, survey_id):
		#check if survey exists		
		if not survey_id in self.current_surveys: return out.SURVEY_UNKNOWN.format(survey_id.upper())
		#check if user already subscrided this survey
		try:
			if not self.get_surveys(user_id)[survey_id]:
				return out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper(), self.bot_name)
			return ""  
		except KeyError: 
			return out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper(), self.bot_name)		

	def __schedule_reminder(self, user_id, survey_id, schedule):
		#if ts is None remove the reminder		
 		if schedule is None:
 			print u"[removing reminder for @{} ({})]".format(user_id, survey_id)
			try:
				for job in self.reminders[(user_id,survey_id)].values():
					job.remove()
			except KeyError:
				pass
		else:
			print u"[setting reminder for @{} ({}): {}]".format(user_id, survey_id, schedule.strftime('%I:%M%p'))			
			period = schedule.strftime('%p')			
			try:				
				job = self.reminders[(user_id,survey_id)][period]					
				#if this reminder already exists, simply update the schedule
				job.reschedule(trigger='cron', hour=schedule.hour, minute=schedule.minute)					
			except KeyError:						
				#else, create new 
				job = self.scheduler.add_job(self.remind_user, 
											 args=[user_id,survey_id.upper(), period.upper()],
											 trigger='cron', hour=schedule.hour, minute=schedule.minute)
				self.reminders[(user_id,survey_id)][period] = job

	def __get_time(self, t):
		try:
			return datetime.strptime(t , '%I:%M%p').time()			
		except ValueError:
			raise RuntimeError(out.INVALID_TIME.format(t))
	
	def __answers_2_indices(self, survey_id, responses):
		new_response = {}
		questions = self.current_surveys[survey_id]["questions"]
		for q in questions:
			q_id = q["q_id"]
			ans = responses[q_id]
			new_response[q_id] = q["choices"].index(ans)
		return new_response

	