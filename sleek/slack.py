from apscheduler.schedulers.background import BackgroundScheduler
from collections import defaultdict
from datetime import datetime
import json
import pprint
from slackclient import SlackClient
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
}
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
				"help": sleek_help,
				"nack": ["sorry, I didn't get that", "I don't understand that command","!?"]
				}

	def __init__(self, db, cfg=default_cfg):				
		assert isinstance(db, Backend)
		self.backend = db
		Sleek.__init__(self, cfg)		
		#{survey_id:survey}
		self.current_surveys = {x[0]:json.loads(x[1]) for x in self.backend.list_surveys()}				
		#reminder scheduler
		self.scheduler = BackgroundScheduler()
		self.scheduler.start()
		#reminders > {(user_id, survey_id):{"am":reminder_am, "pm":reminder_pm}}		
		self.reminders = defaultdict(dict)		
		self.load_reminders()	
		#survey_threads > {thread_id:(user_id, survey_id, response)}
		self.survey_threads = {}						
		self.slack_client = None
		self.team_id = None
		self.bot_name = None


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
	

	#################################################################
	# CORE METHODS
	#################################################################	

	def connect(self, api_token, bot_name, team_id, greet_channel=None, verbose=False, dbg=False):
		self.slack_client = SlackClient(api_token)				
		self.slackers = self.get_slackers()
		self.id2user  = {uid:uname for uname, uid in self.slackers.items()}
		self.team_id  = team_id
		self.bot_name = bot_name
		#open direct messages		
		self.direct_messages = self.current_dms() #{self.open_dm(u):u for u in self.slackers.values() if u is not None}		
 		if greet_channel is not None: 
 			self.post(greet_channel, self.greet())
 			self.post(greet_channel, self.announce("*@{}*".format(self.bot_name)))
		if self.slack_client.rtm_connect():
			# self.post_attach("#general", "wussup?")
			self.__listen(verbose, dbg)
		else:
			raise RuntimeError("Could not connect to RTM API :(")

	def get_surveys(self, user_id):
		us = self.backend.list_surveys(user_id)		
		user_surveys  = {x[1]:None for x in us}				
		surveys = {s:True if s in user_surveys else False for s in self.current_surveys.keys()}				
		return surveys		

	def __listen(self, verbose=False, dbg=False):
		"""
			verbose == True, print all the events of type "message"
			dbg == True, allow unhandled exceptions
		"""
		hat_bot = "<@{}>".format(self.slackers[self.bot_name]).lower() 
		while True:		
			reply = None	
			for output in self.slack_client.rtm_read():					
				if output["type"] != "message" or 'bot_id' in output: continue
				if verbose and not 'bot_id' in output:
					print "DBG:\n"
					pprint.pprint(output)
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
					#remove bot mention
   					text = text.replace(hat_bot,"").strip()			   							
			   		self.ongoing_survey(text, context)	   			
				#or messages directed at the bot						   	
				elif hat_bot in text or channel in self.direct_messages:
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
		   					self.post(channel, reply, thread_ts)

				print "[waiting for @{}...]".format(self.bot_name)				
				time.sleep(READ_WEBSOCKET_DELAY)

	def parse_answer(self, survey_thread, text):
		open_user, open_survey, open_response = self.survey_threads[survey_thread]		
		#case where the user already answered the questions and 
		#chose to add notes
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
				return [out.ANSWERS_INVALID]
			#incorrect number of answers
			if len(answers) > len(questions):
				return [out.ANSWERS_TOO_MANY.format(len(questions), len(answers))]
			elif len(answers) < len(questions):
				return [out.ANSWERS_TOO_FEW.format(len(questions), len(answers))]
			#response dictionary
			response = {}
			for q, a in zip(questions, answers):
				q_id = q["q_id"]
				choices = q["choices"]
				if a not in range(len(choices)):
					return [out.ANSWERS_BAD_CHOICE.format(q["q_id"])]
				else:
					response[q_id] = choices[a]		
		#cache this response
		self.survey_threads[survey_thread] = (open_user, open_survey, response)		
		attach = display.attach_answer(response, open_survey)		
		return [out.ANSWERS_CONFIRM, attach]

	def save_answer(self, survey_thread):
		user_id, survey_id, response  = self.survey_threads[survey_thread]
		if response is None: return [out.ANSWERS_INVALID]
		try:			
			del self.survey_threads[survey_thread]
			ts = datetime.now().strftime('%Y-%m-%d %H:%M')
			response["ts"]=ts
			if not self.backend.save_answer(user_id, survey_id, response):
				return [out.ANSWERS_SAVE_FAIL]
		except RuntimeError:
			return [out.ANSWERS_SAVE_FAIL]
		return [out.ANSWERS_SAVE_OK]

	def remind_user(self, user_id, survey_id, period):
		self.post(user_id, out.REMIND_SURVEY.format(survey_id,period))				
		
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
	# BOT ACTION METHODS
	#################################################################	
	
	########## ANSWER METHODS	

	def cmd_delete(self, tokens, context):
		user_id = context["user_id"]				
		survey_id = tokens[1]	
		#check if user can delete answers to this survey
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return [err_msg]
		r = self.backend.delete_answers(user_id, survey_id)
		if r > 0: return [out.ANSWERS_DELETE_OK.format(survey_id.upper())]
		else:	  return [out.ANSWERS_DELETE_FAIL.format(survey_id.upper())]

	def cmd_survey(self, tokens, context, present=True):
		user_id = context["user_id"]
		survey_id = tokens[1]
		#check if user can open this survey
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return [err_msg]
		#register this thread as an open survey
		self.survey_threads[context["thread_ts"]] = (user_id, survey_id, None)
		s = self.current_surveys[survey_id]
		if present: return [self.ack(), display.attach_survey(s)]
		else:       return [s]

	################ SURVEY METHODS			

	def cmd_join(self, tokens, context):
		user_id = context["user_id"]						
		survey_id = tokens[1]
		#check if survey exists
		if not survey_id in self.current_surveys: return [out.SURVEY_UNKNOWN.format(survey_id.upper())]
		#check if user already subscrided this survey
		try:
			if self.get_surveys(user_id)[survey_id]:
				return [out.SURVEY_IS_SUBSCRIBED.format(survey_id.upper())]
		except KeyError: 
			pass		
		#all the remainder tokens have to be valid dates
		for t in tokens[2:]:
			try:
				_ = self.__get_time(t)				
			except RuntimeError as e:
				return [str(e)]
		try:
			#try to join survey					
			if not self.backend.join_survey(user_id, survey_id):
				return [out.SURVEY_JOIN_FAIL.format(survey_id.upper())]
		except RuntimeError as e:			
			return [out.SURVEY_JOIN_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))]
		
		if len(tokens) > 2:
			rep = self.cmd_reminder(tokens, context)
			if type(rep) == list:				
				return [self.ack(), out.SURVEY_JOIN_OK.format(survey_id.upper()), rep[1]]
			else:
				return [self.ack(), out.SURVEY_JOIN_OK.format(survey_id.upper()), rep]
		return [self.ack(), out.SURVEY_JOIN_OK.format(survey_id.upper())]
		
	def cmd_leave(self, tokens, context):
		user_id = context["user_id"]
		survey_id = tokens[1]		
		#check if user can leave survey
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return [err_msg]
		if not self.backend.leave_survey(user_id, survey_id):
			return [out.SURVEY_LEAVE_FAIL.format(survey_id.upper())]
		return [self.ack(), out.SURVEY_LEAVE_OK.format(survey_id.upper())]

	

	def cmd_list(self, tokens, context):
		user_id = context["user_id"]
		us = self.backend.list_surveys(user_id)		
		user_surveys  = {x[1]:(x[2],x[3]) for x in us}
		other_surveys = [s for s in self.current_surveys.keys() if s not in user_surveys]	
		# display.survey_list(user_surveys,other_surveys)		
		return [display.attach_survey_list(user_surveys,other_surveys)]
	
	################  REPORT METHODS
	
	def cmd_report(self, tokens, context):
		user_id = context["user_id"]
		survey_id = tokens[1]
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return [err_msg]
		try:
			rep = self.backend.get_report(user_id, survey_id)
			if len(rep) == 0:
				return [out.REPORT_EMPTY.format(survey_id.upper())]
			notez = self.backend.get_notes(user_id, survey_id)
			report_attach = display.attach_report(self.current_surveys[survey_id], rep, notez)
			return [self.ack(), report_attach]
		except RuntimeError as e:
			return [out.REPORT_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))]	
	
	################  REMINDER METHODS

	def cmd_reminder(self, tokens, context):
		user_id = context["user_id"]				
		survey_id = tokens[1]
		#check if user can add reminder to this survey
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return [err_msg]
		if tokens[2] == "remove":			
			#remove reminder schedule 
			if not self.backend.set_reminder(user_id, survey_id, None):
				return [out.REMINDER_FAIL.format(survey_id)]
			#remove reminder triggers
			self.__schedule_reminder(user_id, survey_id, None)			
			return [self.ack(), out.REMINDER_REMOVE_OK.format(survey_id.upper())]				
		#collect schedules
		am_schedule,pm_schedule = None, None
		for t in tokens[1:]:
			try:
				if   "am" in t:	am_schedule = self.__get_time(t)
				elif "pm" in t: pm_schedule = self.__get_time(t)						
			except RuntimeError as e:
				return [str(e)]
		#if no valid schedules were provided, leave immediatelly
		if am_schedule is None and pm_schedule is None: return [out.REMINDER_FAIL.format(survey_id), "invalid schedules"]	
		#else, set new reminders
		for reminder in [am_schedule,pm_schedule]:	
			if reminder is not None: 
				#save new reminder schedule
				if not self.backend.set_reminder(user_id, survey_id, reminder.strftime('%I:%M%p')):
					return [out.REMINDER_FAIL.format(survey_id), "failed to update the DB"]
				#set new reminder trigger
				self.__schedule_reminder(user_id, survey_id, reminder)					
		#choose a return message
		if am_schedule is not None and pm_schedule is not None:
			am = am_schedule.strftime('%I:%M%p')
			pm = pm_schedule.strftime('%I:%M%p')
			return [self.ack(), out.REMINDER_OK_2.format(survey_id.upper(), am, pm)]
		elif am_schedule is not None:			
			am = am_schedule.strftime('%I:%M%p')		
			return [self.ack(), out.REMINDER_OK.format(survey_id.upper(), am)]
		elif pm_schedule is not None:				
			pm = pm_schedule.strftime('%I:%M%p')
			return [self.ack(), out.REMINDER_OK.format(survey_id.upper(), pm)]
		else:
			return [out.REMINDER_FAIL.format(survey_id), "??"]

	#################################################################
	#  INTERACTIONS
	#################################################################

	def process(self, text, context):
		user_id = context["user_id"]
		channel = context["channel"]
		thread_ts = context["thread_ts"]
		tokens = text.split()
		action = tokens[0]
		params =  u','.join(tokens[1:])		
		print u"[user: {}| action: {}({})]".format(user_id, action, params)						
		print "chat chan:{}".format(channel)
		#Actions
		# ---- DELETE DATA ----
		if action == "delete":			
			if len(tokens) < 2: 
				replies = [out.MISSING_PARAMS]			
			else:
				replies = self.cmd_delete(tokens, context)			
		
		# ---- JOIN SURVEY ----
		elif action == "join":			
			if len(tokens) < 2: 
				replies = [out.MISSING_PARAMS]
			else:
				replies = self.cmd_join(tokens, context)

		# ---- LEAVE SURVEY ----
		elif action == "leave":	
			if len(tokens) < 2: 
				replies = [out.MISSING_PARAMS]					
			else:
				replies = self.cmd_leave(tokens, context)											

		# ---- LIST SURVEYS ----
		elif action == "list": 
			replies = self.cmd_list(tokens, context)	
			attach = replies.pop()
			pprint.pprint(attach)			
			self.post(channel, "", thread_ts, attach=attach)

		# ---- SHOW REPORT ----
		elif action == "report":					
			if len(tokens) < 2: 
				replies = [out.MISSING_PARAMS]	
			else:				
				replies = self.cmd_report(tokens, context)		
				#if there is only one message, then this is an error (sucess returns an ack and the reply)
				if len(replies) > 1:
					atch = replies.pop()
					for r in replies:
						self.post(channel, r, thread_ts)
					self.post(channel, "", thread_ts, attach=atch)						
					replies = []
		
		# ---- SCHEDULE SURVEY ----
		elif action == "reminder":	
			if len(tokens) < 3: 
				replies = [out.MISSING_PARAMS]											
			else:
				replies = self.cmd_reminder(tokens, context)

		# ---- ANSWER SURVEY ----
		elif action == "survey":
			if len(tokens) < 2: 
				replies = [out.MISSING_PARAMS]
			else:
				replies = self.cmd_survey(tokens, context)
				atch = replies.pop()
				for r in replies:
					self.post(channel, r, thread_ts)
				self.post(channel, "", thread_ts, attach=atch)							
				replies = []

		# ---- PASS IT TO THE PARENT CLASS (maybe it knows how to handle this input)
		else:
			replies = Sleek.chat(self, tokens, context)
		#post replies				
		for r in replies: self.post(channel, r, thread_ts)

	def ongoing_survey(self, text, context):		
   		tokens = text.split()
   		channel = context["channel"]
   		thread_ts = context["thread_ts"]
		if tokens[0] == "cancel":
			#remove current thread from open survey threads
			del self.survey_threads[thread_ts]
			reply = [self.ack(), out.SURVEY_CANCELED]
		elif tokens[0] == "ok":
			#save answer and close survey
			reply = self.save_answer(thread_ts)
		elif tokens[0] == "notes":
			open_user, open_survey, response = self.survey_threads[thread_ts] 
			#add a placeholder for the notes on the response
			response["notes"]=""
			self.survey_threads[thread_ts] = (open_user, open_survey, response)
			reply = [self.ack(), out.ANSWERS_ADD_NOTE]						
		else:
   			reply = self.parse_answer(thread_ts, text)
   			if len(reply) > 1:
   				#ok
   				attach = reply.pop()   		
   				self.post(channel, "", thread_ts, attach)
   				for r in reply: self.post(channel, r, thread_ts)   				
   				reply = []
   		
		for r in reply: self.post(channel, r, thread_ts)
		
   		
	def greet_user(self, text, context):
		#open new DM
		user = context["user_id"]		
		channel = context["channel"]
		new_dm = self.open_dm(user)						
		self.direct_messages[new_dm] = user					
		try:
			username = self.id2user[user]
		except KeyError:
			username=""
		#greet user and move conversation to a private chat
		self.post(channel, out.GREET_USER.format(self.greet(), username))		
		#say hi on the new DM		
		self.post(new_dm, "> *you said*: _{}_\n\n".format(text))
		context["channel"] = new_dm
		context["thread_ts"] = None
		
		return context

	#################################################################
	#  SLACK API METHODS
	#################################################################

	def post(self, channel, message, ts=None, attach=None):		
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

	
	def get_slackers(self):
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

	def current_dms(self):
		resp = self.slack_client.api_call("im.list")		
		if not resp.get("ok"): 						
			print "\033[31m[error: {}]\033[0m".format(resp["error"])
			return []
		else:
			 dm_ids = {r["id"]:r["user"] for r in resp["ims"] if not r["is_user_deleted"]}
			 return dm_ids
	
