from apscheduler.schedulers.background import BackgroundScheduler
from collections import defaultdict
from datetime import datetime
from ipdb import set_trace
import json
import os
from string import ascii_letters


#sleek
from backend import Backend
from kafka_backend import KafkaBackend
from bots import ChatBot
import out
import display


class Survey(object):

	def __init__(self, survey):
		self.survey_id = survey["id"]
		self.question_ids = [q["q_id"] for q in survey["questions"]]
		self.questions = {q["q_id"]:q for q in survey["questions"]}
		self.answers = {q["q_id"]:None for q in survey["questions"]}
		self.note = None

	def answer(self, q_id, a):
		"""
			Answer a survey question
			========================
			q_id - question id
			a    - answer to question q_id (i.e., the index to the choices associated to this question)
		"""		
		try:
			choices = self.questions[q_id]["choices"]					
		except KeyError:
			return False

		if a not in range(len(choices)):
			return False 
		else:
			self.answers[q_id] = a
			return True
	
	def add_note(self, note):
		"""
			Add a note to this survey
			=========================
			note - a text note
		"""
		self.note = note

class User(object):	

	def __init__(self, user_id, user_name, sleek):		
		self.user_name = user_name
		self.user_id = user_id		
		self.sleek = sleek
		my_surveys = self.sleek.backend.list_surveys(user_id)
		#dictionary {survey_id: (am_reminder, pm_reminder)}
		self.surveys = {s[1]:(None,None) for s in my_surveys}
		#load reminders				
		for s_id, am, pm in self.sleek.backend.get_reminders(self.user_id):
			if am is not None: 
				am = datetime.strptime(am , '%I:%M%p').time()				
				self.sleek.set_reminder(user_id, s_id, am)				
			if pm is not None: 
				pm = datetime.strptime(pm , '%I:%M%p').time()
				self.sleek.set_reminder(user_id, s_id, pm)	
			self.surveys[s_id] = (am, pm)
	
	def join_survey(self, survey_id):
		self.sleek.backend.join_survey(self.user_id, survey_id)		
		self.surveys[survey_id] = (None, None)
	
	def save_reminder(self, survey_id, am_reminder=None, pm_reminder=None):
		#save and set reminders
		self.surveys[survey_id] = (am_reminder, pm_reminder)
		if am_reminder is not None:			
			self.sleek.backend.save_reminder(self.user_id, survey_id, am_reminder)				
			self.sleek.set_reminder(self.user_id, survey_id, am_reminder)
		if pm_reminder is not None:			
			self.sleek.backend.save_reminder(self.user_id, survey_id, pm_reminder)		
			self.sleek.set_reminder(self.user_id, survey_id, pm_reminder)				

	def leave_survey(self, survey_id):
		del self.surveys[survey_id]
		self.sleek.backend.leave_survey(self.user_id, survey_id)
		#unset reminder
		self.sleek.set_reminder(self.user_id, survey_id, None)

class Sleek(ChatBot):

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

	default_cfg = { "announce": sleek_announce,				
				    "help": "\n".join(help_dict.values())
				  }

	def __init__(self, confs, init_db=False):

		ChatBot.__init__(self, Sleek.default_cfg)		
		if confs["backend_type"]=="local":
			self.backend = Backend(confs, init=init_db)
		elif confs["backend_type"]=="kafka":
			self.backend = KafkaBackend(confs, init=init_db)		
		else:
			raise NotImplementedError
		 
		self.surveys = {x[0]:json.loads(x[1]) for x in self.backend.list_surveys()}
		self.reminders = defaultdict(dict)
		self.users = None				
		self.interactive = False
		self.bot_name = "silvio"
		self.scheduler = BackgroundScheduler()
		self.scheduler.start()

	def load_users(self, users):
		"""
			Load Users
			##########
			users - dictionary {user_name:user_id}			
		"""			
		self.users = {uid: User(uid, uname, self) for uname, uid in users.items()}		

	
	#################################################################
	# BOT COMMAND METHODS
	#################################################################		

	def cmd_add_reminder(self, tokens, context):
		"""	
			Add a reminder for user/survey
			==============================
			user_id   - user id
			survey_id - survey id
		"""
		if len(tokens) < 2: 			
			return [self.oops(), out.MISSING_PARAMS]
		survey_id = tokens[1]	
		user_id = context["user_id"]	
		try:
			am_reminder, pm_reminder = parse_reminders(tokens[2:])
		except ValueError as e:
			return [self.oops, e.message]
		
		self.users[user_id].save_reminder(survey_id, am_reminder, pm_reminder)		
		#choose a return message
		if am_reminder is not None and pm_reminder is not None:			
			txt = out.REMINDER_OK_2.format(survey_id.upper(), 
										   am_reminder, pm_reminder)					
		elif am_reminder is not None:						
			txt = out.REMINDER_OK.format(survey_id.upper(), am_reminder)
		elif pm_reminder is not None:							
			txt = out.REMINDER_OK.format(survey_id.upper(), pm_reminder)
		else:
			return [self.oops(), out.REMINDER_FAIL.format(survey_id)]
		 
	 	return [self.ack(), txt]


	def cmd_delete(self, tokens, context):
		"""
			Delete answers to a survey
			=========================
			user_id   - user id
			survey_id - survey id
		"""	
		if len(tokens) < 2: 			
			raise RuntimeError("Missing Parameters")
		
		survey_id = tokens[1]	
		user_id = context["user_id"]							
		#check if user can delete answers to this survey			
		e = self.__is_valid_survey(user_id, survey_id)
		if len(e) > 0: raise RuntimeError(e) 
		
		if not self.backend.delete_answers(user_id, survey_id):
			e = out.ANSWERS_DELETE_FAIL.format(survey_id.upper())
			raise RuntimeError(e) 

	def cmd_join(self, tokens, context):
		"""	
			Join a survey
			=============		
		"""		
		if len(tokens) < 2: 	
			return [self.oops(), out.MISSING_PARAMS]					
		
		survey_id = tokens[1]
		user_id = context["user_id"]											
		#check if survey exists
		if not survey_id in self.surveys: 				
			return [self.oops(), out.SURVEY_UNKNOWN.format(survey_id.upper())]

		#first validate reminder schedules
		try:			
			am_reminder, pm_reminder = parse_reminders(tokens[2:])
		except ValueError as e:
			return [self.oops(), e.message]
		#join survey
		try:
			self.users[user_id].join_survey(survey_id)
			#try to set reminders
			if am_reminder is not None or pm_reminder is not None:
				rm = self.cmd_add_reminder(tokens, context)			
			return [self.ack(), out.SURVEY_JOIN_OK.format(survey_id.upper()), rm[1]]
		except RuntimeError as r:		
			e  = out.SURVEY_JOIN_FAIL.format(survey_id.upper())
			e += " [err: {}]".format(str(r))		
			return [self.oops(), e]

	def cmd_leave(self, tokens, context):
		"""	
			Leave a survey
			=============
			user_id   - user id
			survey_id - survey id
		"""
		if len(tokens) < 2: 			
			return [self.oops(), out.MISSING_PARAMS]					
		
		survey_id = tokens[1]
		user_id = context["user_id"]									
		if not survey_id in self.surveys: 				
			return [self.oops(), out.SURVEY_UNKNOWN.format(survey_id.upper())]
		
		try:		
			self.users[user_id].leave_survey(survey_id)				
			return [self.ack(), out.SURVEY_LEAVE_OK.format(survey_id.upper())]
			#set reminder
			if len(tokens)>2: self.cmd_reminder(tokens, context)
		except RuntimeError as r:		
			e  = out.SURVEY_LEAVE_FAIL.format(survey_id.upper())
			e += " [err: {}]".format(str(r))		
			return [self.oops(), e]
		
	def cmd_list(self, tokens, context):
		"""	
			List user surveys
			=============			
		"""
		user_id = context["user_id"]
		user_surveys = self.users[user_id].surveys
		other_surveys = list(set(self.surveys.keys()) - set(user_surveys))		
		output = display.survey_list(user_surveys, other_surveys)
		return [self.ack(), output]

	def read(self, text, context):
		user_id = context["user_id"]		
		tokens = text.split()
		action = tokens[0]
		params =  u','.join(tokens[1:])		
		print u"[user: {}| action: {}({})]".format(user_id, action, params)								
		#Actions
		# # ---- DELETE DATA ----
		if action == "delete": return self.cmd_delete(tokens, context)			
		
		# ---- JOIN SURVEY ----
		elif action == "join": return self.cmd_join(tokens, context)			
			
		# ---- LEAVE SURVEY ----
		elif action == "leave": return self.cmd_leave(tokens, context)			
			
		# ---- LIST SURVEYS ----
		elif action == "list": return self.cmd_list(tokens, context)			

		# ---- SHOW REPORT ----
		# elif action == "report": 
		# 	self.cmd_report(tokens, context)
		# 	return "OK"
		
		#---- SCHEDULE SURVEY ----
		elif action == "reminder": 
			if "remove" not in tokens: return self.cmd_add_reminder(tokens, context)
			else:               return self.cmd_remove_reminder(tokens, context)

		# ---- ANSWER SURVEY ----
		# elif action == "survey": 
		# 	self.cmd_survey(tokens, context)
		
		# else:
		# 	return "damn brah..."
			# raise NotImplementedError

		#---- PASS IT TO THE PARENT CLASS (maybe it knows how to handle this input)
		else: return ChatBot.chat(self, tokens, context)		
			
	
	# def remind_user(self, user_id, survey_id, period):
	# 	raise NotImplementedError
	

	# def cmd_remove_reminder(self, tokens, context):
	# 	"""	
	# 		Remove reminders for user/survey
	# 		==============================
	# 		user_id   - user id
	# 		survey_id - survey id
	# 	"""
	# 	pass		

	# def cmd_report(self, tokens, context):
	# 	"""	
	# 		Show report
	# 		=============
	# 		user_id   - user id
	# 		survey_id - survey id
	# 	"""
		
	# 	report = self.backend.get_report(user_id, survey_id)
	# 	notes = self.backend.get_notes(user_id, survey_id)
		
	# 	return report, notes

	#################################################################
	# AUX METHODS
	#################################################################		

	def set_reminder(self, user_id, survey_id, schedule):
		return 

		#if ts is None remove the reminder		
 		if schedule is None:
 			print u"[removing reminder for @{} ({})]".format(user_id, survey_id)
			try:
				for job in self.reminders[(user_id,survey_id)].values():
					job.remove()
			except KeyError:
				pass
		else:
			print u"[setting reminder for @{} ({}): {}]".format(user_id, 
																survey_id, 
																schedule.strftime('%I:%M%p'))			
			period = schedule.strftime('%p')			
			try:				
				job = self.reminders[(user_id,survey_id)][period]					
				#if this reminder already exists, simply update the schedule
				job.reschedule(trigger='cron', hour=schedule.hour, 
							   minute=schedule.minute)					
			except KeyError:						
				#else, create new 
				job = self.scheduler.add_job(self.remind_user, 
											 args=[user_id,survey_id.upper(), 
											 	  period.upper()],
											 	  trigger='cron', 
											 	  hour=schedule.hour, 
											 	  minute=schedule.minute)
				self.reminders[(user_id,survey_id)][period] = job
	
	
	def load_surveys(self, survey_path):
		"""
			Loads surveys in batch mode
			survey_path: path to folder containing surveys in json format
		"""

		print "[loading surveys @ {}]".format(survey_path)
		ignored = []
		for fname in os.listdir(survey_path):	
			path = survey_path+fname
			if os.path.splitext(path)[1]!=".json":
				ignored.append(fname)			
				continue	
			try:		
				with open(path, 'r') as f:					
					try:
						survey = json.load(f)				
					except ValueError:
						print "invalid json @{}".format(fname)
						continue
					try:
						self.backend.create_survey(survey)			
					except RuntimeError as e:
						print e

			except IOError:
				ignored.append(path)	
		if len(ignored) > 0:
			print "[ignored the files: {}]".format(repr(ignored))

def parse_reminders(tokens):
	am_reminder,pm_reminder = None, None
	#validate input times by trying to convert to datetime
	for t in tokens:	
		try:
			if   "am" in t: am_reminder = datetime.strptime(t , '%I:%M%p').time()					
			elif "pm" in t: pm_reminder = datetime.strptime(t , '%I:%M%p').time()					
		except ValueError:		
			raise ValueError(out.INVALID_TIME.format(t))
	#convert back to strings 
	if am_reminder is not None: am_reminder = am_reminder.strftime('%I:%M%p')
	if pm_reminder is not None: pm_reminder = pm_reminder.strftime('%I:%M%p')

	return am_reminder, pm_reminder

	# def run_survey(self, text, context):
 #   		tokens = text.split()
 #   		channel = context["channel"]
 #   		thread_ts = context["thread_ts"]
 #   		error = ""
	# 	if tokens[0] == "cancel":
	# 		#remove current thread from open survey threads
	# 		del self.survey_threads[thread_ts]			
	# 		post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)
	# 		post_slack(self.slack_client, channel, out.SURVEY_CANCELED, ts=thread_ts)
	# 	elif tokens[0] == "ok":
	# 		open_user, open_survey, open_channel, response = self.survey_threads[thread_ts] 			
	# 		if response is None: 
	# 			post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)
	# 			post_slack(self.slack_client, channel, out.ANSWERS_INVALID, ts=thread_ts)
	# 		else:
	# 			response = self.__answers_2_indices(open_survey, response)
	# 			ts = datetime.now().strftime('%Y-%m-%d %H:%M')				
	# 			response["ts"]=ts
	# 			if not self.backend.save_answer(open_user, open_survey, response):			
	# 				post_slack(self.slack_client, channel, out.ANSWERS_SAVE_FAIL, ts=thread_ts)
	# 			else:
	# 				#if saved ok, remove this survey from the open threads
	# 				del self.survey_threads[thread_ts]
	# 				post_slack(self.slack_client, channel, out.ANSWERS_SAVE_OK, ts=thread_ts)
	# 	elif tokens[0] == "notes":
	# 		open_user, open_survey, open_channel, response = self.survey_threads[thread_ts] 
	# 		#add a placeholder for the notes on the response
	# 		response["notes"]=""
	# 		self.survey_threads[thread_ts] = (open_user, open_survey, channel, response)
	# 		post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)
	# 		post_slack(self.slack_client, channel, out.ANSWERS_ADD_NOTE, ts=thread_ts)						
	# 	else:
	# 		#parse the answer			
	# 		open_user, open_survey, open_channel, open_response = self.survey_threads[thread_ts]					
	# 		#case where the user already answered the questions and 
	# 		#is adding a note
	# 		if open_response is not None and "notes" in open_response:
	# 			response = open_response
	# 			response["notes"] = text				
	# 		else:
	# 			#otherwise these should be answers to the survey
	# 			questions = self.current_surveys[open_survey]["questions"]		
	# 			#assumes responses are separated by white spaces		
	# 			try:
	# 				#answers are indices into a list of choices
	# 				answers = [ascii_letters.index(a) for a in text.split()]
	# 			except ValueError:
	# 				error = out.ANSWERS_INVALID
	# 			if len(error) == 0:
	# 				#incorrect number of answers
	# 				if len(answers) > len(questions):
	# 					error = out.ANSWERS_TOO_MANY.format(len(questions), len(answers))
	# 				elif len(answers) < len(questions):
	# 					error = out.ANSWERS_TOO_FEW.format(len(questions), len(answers))				
	# 			if len(error) == 0:
	# 				#response dictionary
	# 				response = {}
	# 				for q, a in zip(questions, answers):
	# 					q_id = q["q_id"]
	# 					choices = q["choices"]
	# 					if a not in range(len(choices)):
	# 						error = out.ANSWERS_BAD_CHOICE.format(q["q_id"])
	# 						break
	# 					else:
	# 						response[q_id] = choices[a]		
	# 		if len(error) == 0:
	# 			#cache this response
	# 			self.survey_threads[thread_ts] = (open_user, open_survey, open_channel, response)		
	# 			attach = display.attach_answer(response, open_survey, cancel_button=False)		
	# 			post_slack(self.slack_client, channel, "", ts=thread_ts, attach=attach)
	# 			post_slack(self.slack_client, channel, out.ANSWERS_CONFIRM, ts=thread_ts)					
	# 		else:
	# 			post_slack(self.slack_client, channel, error, ts=thread_ts)

	# def interactive_survey(self, text, context):
 #   		tokens = text.split()
 #   		channel = context["channel"]
 #   		thread_ts = context["thread_ts"]
 #   		error = ""
	# 	if tokens[0] == "cancel":
	# 		#remove current thread from open survey threads
	# 		del self.survey_threads[thread_ts]			
	# 		post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)
	# 		post_slack(self.slack_client, channel, out.SURVEY_CANCELED, ts=thread_ts)
	# 	elif tokens[0] == "ok":
	# 		open_user, open_survey, open_channel, response = self.survey_threads[thread_ts] 			
	# 		if response is None: 
	# 			post_slack(self.slack_client, channel, self.oops(), ts=thread_ts)
	# 			post_slack(self.slack_client, channel, out.ANSWERS_INVALID, ts=thread_ts)
	# 		else:
	# 			response = self.__answers_2_indices(open_survey, response)
	# 			#record timestamp
	# 			ts = datetime.now().strftime('%Y-%m-%d %H:%M')
	# 			response["ts"]=ts
	# 			if not self.backend.save_answer(open_user, open_survey, response):			
	# 				post_slack(self.slack_client, channel, out.ANSWERS_SAVE_FAIL, ts=thread_ts)
	# 			else:
	# 				#if saved ok, remove this survey from the open threads
	# 				del self.survey_threads[thread_ts]
	# 				post_slack(self.slack_client, channel, out.ANSWERS_SAVE_OK, ts=thread_ts)
	# 	elif tokens[0] == "notes":
	# 		open_user, open_survey, open_channel, response = self.survey_threads[thread_ts] 
	# 		#add a placeholder for the notes on the response
	# 		response["notes"]=""
	# 		self.survey_threads[thread_ts] = (open_user, open_survey, open_channel, response)
	# 		post_slack(self.slack_client, channel, self.ack(), ts=thread_ts)
	# 		post_slack(self.slack_client, channel, out.ANSWERS_ADD_NOTE, ts=thread_ts)						
	# 	else:
	# 		#parse the answer						
	# 		open_user, open_survey, open_channel, open_response = self.survey_threads[thread_ts]		
	# 		questions = self.current_surveys[open_survey]["questions"]		
	# 		#case where the user already answered the questions and 
	# 		#is adding a note
	# 		if open_response is not None and "notes" in open_response:
	# 			response = open_response
	# 			response["notes"] = text				
	# 		else:
	# 			#otherwise these should be answers to the survey
	# 			if open_response is not None:
	# 				#continue
	# 				response = open_response
	# 			else:
	# 				#this is a brand new answer
	# 				response = {}				
	# 			tokens = text.split()			
	# 			if len(tokens) != 2:
	# 				error = out.ANSWERS_INVALID
	# 			if len(error) == 0 :
	# 				q_index, answer = tokens
	# 				try:
	# 					q_index = int(q_index)
	# 					answer = int(answer)
	# 				except ValueError:
	# 					error = out.ANSWERS_INVALID
	# 				if q_index < 0 or \
	# 				   q_index > len(questions)-1 or \
	# 				   answer < 0:
	# 					error = out.ANSWERS_INVALID					
	# 			if len(error) == 0 :
	# 				question = questions[q_index]
	# 				q_id = question["q_id"]
	# 				choices = question["choices"]					
	# 				if answer not in range(len(choices)):
	# 					error = out.ANSWERS_BAD_CHOICE.format(q_id)
	# 				else:
	# 					response[q_id] = choices[answer]				

	# 		if len(error) == 0:
	# 			#cache this response
	# 			self.survey_threads[thread_ts] = (open_user, open_survey, open_channel, response)		
	# 			#repost the survey
	# 			survey = self.current_surveys[open_survey]		
	# 			attach_survey = display.attach_survey(survey)
	# 			post_slack(self.slack_client, channel, "", ts=thread_ts, attach=attach_survey)							
	# 			#post the current answers
	# 			#if the survey is all filled ask to confirm
	# 			if len(response) == len(questions):
	# 				answer_attach = display.attach_answer(response, open_survey, ok_button=True, notes_button=True)	
	# 				post_slack(self.slack_client, channel, "", ts=thread_ts, attach=answer_attach)
	# 				post_slack(self.slack_client, channel, out.ANSWERS_CONFIRM, ts=thread_ts)
	# 			elif len(response) >= len(questions) and "notes" in response:
	# 				answer_attach = display.attach_answer(response, open_survey, ok_button=True)		
	# 				post_slack(self.slack_client, channel, "", ts=thread_ts, attach=answer_attach)
	# 				post_slack(self.slack_client, channel, out.NOTE_CONFIRM, ts=thread_ts)
	# 			else:
	# 				attach = display.attach_answer(response, open_survey)		
	# 				post_slack(self.slack_client, channel, "", ts=thread_ts, attach=attach)
	# 		else:
	# 			post_slack(self.slack_client, channel, error, ts=thread_ts)
   	

	
