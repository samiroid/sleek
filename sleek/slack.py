from apscheduler.schedulers.background import BackgroundScheduler
from collections import defaultdict
from datetime import datetime
import json
import pprint
import pandas as pd
from slackclient import SlackClient
import out
import time

#sleek
from backend import LocalBackend as Backend
from _sleek import Sleek

# try:	
# 	from ipdb import set_trace
# except ImportError:
# 	from pdb import set_trace

READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose

class Sleek4Slack(Sleek):
	sleek_announce = ''' I am Sleek4Slack, the chat bot :robot_face: -- If we never met, you can start by typing `help` '''	
	
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


	#################################################################
	# PRIVATE METHODS
	#################################################################		

	def __is_valid_survey(self, user_id, survey_id):
		#check if survey exists		
		if not survey_id in self.current_surveys: return out.SURVEY_UNKNOWN.format(survey_id.upper())
		#check if user already subscrided this survey
		try:
			if not self.__list_surveys(user_id)[survey_id]:
				return out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper())
			return ""  
		except KeyError: 
			return out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper())		

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
		
	def __list_surveys(self, user_id):
		us = self.backend.list_surveys(user_id)		
		user_surveys  = {x[1]:None for x in us}				
		surveys = {s:True if s in user_surveys else False for s in self.current_surveys.keys()}				
		return surveys		

	# methods to format the replies
	def __display_answer(self, a):
		notes = None
		if "notes" in a: notes = a["notes"]			
		ans = u"\n".join(["*{}*: {}".format(f,v) for f,v in a.items() if f!="notes"])
		if notes is not None:
			out = u"Your answers\n>>>{}\n_notes_:```{}```".format(ans,notes)
		else:
			out = u"Your answers\n>>>{}".format(ans)
		return out
		
	def __display_survey(self, survey):
		out = u"*===== _{}_ survey =====* \n".format(survey["id"].upper())
		qst = u"> *{}*: _{}_\n{}"		
		opt = u"`{}`   {}"		
		for i,q in enumerate(survey["questions"]):			
			choices = u"\n".join([opt.format(e,c) for e,c in enumerate(q["choices"])])
			out+= qst.format(q["q_id"], q["question"], choices)
			out+=u"\n\n"
		out += u"*====================*"
		return out		

	def __display_report(self, survey_id, report):
		out = u"*report _{}_*\n\n```{}```"
		s = self.current_surveys[survey_id]["questions"]
		#survey answer tables have the columns: id, user_id, timestamp, answer_1, ... , answer_N, notes
		#keeping only: ts, timestamp, answer_1, ... , answer_N
		df = pd.DataFrame(report).iloc[:,2:-1]		
		df.columns = ["ts"] + [q["q_id"] for q in s]		
		df['ts'] = pd.to_datetime(df['ts']).dt.strftime("%Y-%m-%d %H:%M")
		df.set_index('ts', inplace=True)			
		return out.format(survey_id.upper(), repr(df))	

	def __display_notes(self, survey_id, notes):
		out = u"*notes _{}_*\n\n```{}```"		
		df = pd.DataFrame(notes)
		df.columns = ["ts","notes"]
		df['ts'] = pd.to_datetime(df['ts']).dt.strftime("%Y-%m-%d %H:%M")
		df.set_index('ts', inplace=True)			
		return out.format(survey_id.upper(), repr(df))	

	def __display_survey_list(self, user_surveys, other_surveys):
		active=u">*{}*\t`{}`\t`{}`"
		inactive=u"~{}~"
		us = [active.format(s,r[0],r[1]) for s, r in user_surveys.items()]
		ot = [inactive.format(s) for s in other_surveys]
		display = u"*Your Surveys*\n{}\n{}"
		return display.format("\n".join(us),"\n".join(ot))

	#################################################################
	# CORE METHODS
	#################################################################

	def chat(self, text, context):
		user_id = context["user_id"]
		tokens = text.split()
		action = tokens[0]
		params =  u','.join(tokens[1:])		
		print u"[user: {}| action: {}({})]".format(user_id, action, params)						
		
		#Actions
		# ---- DELETE DATA ----
		if action == "delete":			
			if len(tokens) < 2: return out.MISSING_PARAMS			
			return self.delete(tokens, context)			
		
		# ---- JOIN SURVEY ----
		elif action == "join":			
			if len(tokens) < 2: return out.MISSING_PARAMS
			return self.join(tokens, context)

		# ---- LEAVE SURVEY ----
		elif action == "leave":	
			if len(tokens) < 2: return out.MISSING_PARAMS					
			return self.leave(tokens, context)											

		# ---- LIST SURVEYS ----
		elif action == "list": 
			return self.list_surveys(tokens, context)						

		# ---- SHOW REPORT ----
		elif action == "notes":					
			if len(tokens) < 2: return out.MISSING_PARAMS									
			return self.notes(tokens, context)					

		# ---- SHOW REPORT ----
		elif action == "report":					
			if len(tokens) < 2: return out.MISSING_PARAMS									
			return self.report(tokens, context)			
		
		# ---- SCHEDULE SURVEY ----
		elif action == "reminder":	
			if len(tokens) < 3: return out.MISSING_PARAMS											
			return self.reminder(tokens, context)

		# ---- ANSWER SURVEY ----
		elif action == "survey":
			if len(tokens) < 2: return out.MISSING_PARAMS
			return self.survey(tokens, context)			
		
		# ---- PASS IT TO SLEEK (parent class)
		else:
			resp = Sleek.chat(self, tokens, context)
			return resp

	def connect(self, api_token, bot_name, greet_channel=None, verbose=False, dbg=False):
		self.slack_client = SlackClient(api_token)				
		self.slackers = self.get_slackers()
		self.id2user = {uid:uname for uname, uid in self.slackers.items()}
		#open direct messages
		self.direct_messages = {} #{self.open_dm(u):u for u in self.slackers.values() if u is not None}
 		if greet_channel is not None: 
 			self.post(greet_channel, self.greet())
 			self.post(greet_channel, self.announce()) 			
		if self.slack_client.rtm_connect():
			self.__listen(bot_name, verbose, dbg)
		else:
			raise RuntimeError("Could not connect to RTM API :(")


	def __listen(self, bot_name, verbose=False, dbg=False):
		"""
			verbose == True, print all the events of type "message"
			dbg == True, allow unhandled exceptions
		"""
		hat_bot = "<@{}>".format(self.slackers[bot_name]).lower() 
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
			   		tokens = text.split()
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
				#or messages directed at the bot						   	
				elif hat_bot in text or channel in self.direct_messages:
					#if user is not talking on a direct message with sleek
					#open a new one, and reply there
					if channel not in self.direct_messages:
						new_dm = self.open_dm(user)						
						self.direct_messages[new_dm] = user
						#greet user and move conversation to a private chat
						try:
							username = self.id2user[user]
						except KeyError:
							username=""
						self.post(channel, out.GREET_USER.format(self.greet(), username), thread_ts)
						self.post(new_dm, self.greet())
						channel = new_dm 
						thread_ts = None

					#remove bot mention
			   		text = text.replace(hat_bot,"").strip()			   					   		
			   		if dbg:
			   			#debug mode lets unhandled exceptions explode
			   			reply = self.chat(text, context)			   			
		   			else:
		   				try:
			   				reply = self.chat(text, context)
		   				except Exception as e:	   					
		   					reply = "```[FATAL ERROR: {}]```".format(e)
		   		if reply is None: continue				   	
   				#a reply can be either a message or a list thereof
   				if type(reply) == list: 
   					for r in reply: self.post(channel, r, thread_ts)
				else: 
					self.post(channel, reply, thread_ts)				
				time.sleep(READ_WEBSOCKET_DELAY)

	
	#################################################################
	# BOT ACTION METHODS
	#################################################################	
	
	################ ANSWER METHODS

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
				answers = [int(a) for a in text.split()]
			except ValueError:
				return out.ANSWERS_INVALID
			#incorrect number of answers
			if len(answers) > len(questions):
				return out.ANSWERS_TOO_MANY.format(len(questions), len(answers))		
			elif len(answers) < len(questions):
				return out.ANSWERS_TOO_FEW.format(len(questions), len(answers))		
			#response dictionary
			response = {}
			for q, a in zip(questions, answers):
				q_id = q["q_id"]
				choices = q["choices"]
				if a not in range(len(choices)):
					return out.ANSWERS_BAD_CHOICE.format(q["q_id"])
				else:
					response[q_id] = choices[a]		
		#cache this response
		self.survey_threads[survey_thread] = (open_user, open_survey, response)		
		return [self.__display_answer(response), out.ANSWERS_CONFIRM]

	def save_answer(self, survey_thread):
		user_id, survey_id, response  = self.survey_threads[survey_thread]
		if response is None: return out.ANSWERS_INVALID
		try:			
			del self.survey_threads[survey_thread]
			ts = datetime.now().strftime('%Y-%m-%d %H:%M')
			response["ts"]=ts
			if not self.backend.save_answer(user_id, survey_id, response):
				return out.ANSWERS_SAVE_FAIL			
		except RuntimeError:
			return out.ANSWERS_SAVE_FAIL		
		return out.ANSWERS_SAVE_OK

	def delete(self, tokens, context):
		user_id = context["user_id"]				
		survey_id = tokens[1]	
		#check if user can delete answers to this survey
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return err_msg
		r = self.backend.delete_answers(user_id, survey_id)
		if r > 0: return out.ANSWERS_DELETE_OK.format(survey_id.upper())
		else:	  return out.ANSWERS_DELETE_FAIL.format(survey_id.upper())

	################ SURVEY METHODS

	def join(self, tokens, context):
		user_id = context["user_id"]						
		survey_id = tokens[1]
		#check if survey exists
		if not survey_id in self.current_surveys: return out.SURVEY_UNKNOWN.format(survey_id.upper())
		#check if user already subscrided this survey
		try:
			if self.__list_surveys(user_id)[survey_id]:
				return out.SURVEY_IS_SUBSCRIBED.format(survey_id.upper())
		except KeyError: 
			pass		
		#all the remainder tokens have to be valid dates
		for t in tokens[2:]:
			try:
				_ = self.__get_time(t)				
			except RuntimeError as e:
				return str(e)		
		try:
			#try to join survey					
			if not self.backend.join_survey(user_id, survey_id):
				return out.SURVEY_JOIN_FAIL.format(survey_id.upper())
		except RuntimeError as e:			
			return out.SURVEY_JOIN_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))		
		
		if len(tokens) > 2:
			rep = self.reminder(tokens, context)
			if type(rep) == list:				
				return [self.ack(), out.SURVEY_JOIN_OK.format(survey_id.upper()), rep[1]]
			else:
				return [self.ack(), out.SURVEY_JOIN_OK.format(survey_id.upper()), rep]
		return [self.ack(), out.SURVEY_JOIN_OK.format(survey_id.upper())]
		
	def leave(self, tokens, context):
		user_id = context["user_id"]
		survey_id = tokens[1]		
		#check if user can leave survey
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return err_msg
		if not self.backend.leave_survey(user_id, survey_id):
			return out.SURVEY_LEAVE_FAIL.format(survey_id.upper())		
		return [self.ack(), out.SURVEY_LEAVE_OK.format(survey_id.upper())]

	def survey(self, tokens, context, display=True):
		user_id = context["user_id"]
		survey_id = tokens[1]
		#check if user can open this survey
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return err_msg
		#register this thread as an open survey
		self.survey_threads[context["thread_ts"]] = (user_id, survey_id, None)
		s = self.current_surveys[survey_id]
		if display: return [self.ack(),self.__display_survey(s)]
		else:       return s

	def list_surveys(self, tokens, context):
		user_id = context["user_id"]
		us = self.backend.list_surveys(user_id)		
		user_surveys  = {x[1]:(x[2],x[3]) for x in us}
		other_surveys = [s for s in self.current_surveys.keys() if s not in user_surveys]	
		return self.__display_survey_list(user_surveys,other_surveys)	
	
	################  REPORT METHODS
	
	def report(self, tokens, context):
		user_id = context["user_id"]
		survey_id = tokens[1]
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return err_msg
		try:
			rep = self.backend.get_report(user_id, survey_id)
			if len(rep) == 0:
				return out.REPORT_EMPTY.format(survey_id.upper())
			return [self.ack(), self.__display_report(survey_id, rep)]
		except RuntimeError as e:
			return out.REPORT_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))			 	
	
	def notes(self, tokens, context):
		user_id = context["user_id"]
		survey_id = tokens[1]
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return err_msg
		try:
			rep = self.backend.get_notes(user_id, survey_id)
			if len(rep) == 0:
				return out.NOTES_EMPTY.format(survey_id.upper())
			return [self.ack(), self.__display_notes(survey_id, rep)]
		except RuntimeError as e:
			return out.REPORT_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))			 	

	################  REMINDER METHODS
	
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

	def reminder(self, tokens, context):
		user_id = context["user_id"]				
		survey_id = tokens[1]
		#check if user can add reminder to this survey
		#if ok err_msg will be empty
		err_msg = self.__is_valid_survey(user_id, survey_id)
		if len(err_msg)>0: return err_msg
		if tokens[2] == "remove":			
			#remove reminder schedule 
			if not self.backend.set_reminder(user_id, survey_id, None):
				return out.REMINDER_FAIL.format(survey_id)
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
				return str(e)
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

	################ SLACK API METHODS	
	def post(self, channel, message, ts=None):
		print u"[posting:\"{}\" to channel {}]".format(message,channel)
		if ts is not None:
			resp = self.slack_client.api_call("chat.postMessage",
	  					 channel=channel,
	  					 as_user=True,
	  					 thread_ts=ts,
	  					 text=message)
		else:
			resp = self.slack_client.api_call("chat.postMessage",
	  					 channel=channel,
	  					 as_user=True,	  					 
	  					 text=message)
		
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
	