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

	def __init__(self, s, user_id):
		self.user_id = user_id
		self.survey = s
		self.id = s["id"]		
		self.questions = s["questions"]
		self.answer_choices = {q["q_id"]:q["choices"] for q in s["questions"]}		
		self.answers = {}		
		self.notes = None

	def put_answers(self, tokens):
		
		try:
			#answers are indices into a list of choices
			ans = [ascii_letters.index(a) for a in tokens]
		except ValueError:
			raise RuntimeError(out.ANSWERS_INVALID)			
		
		#incorrect number of answers
		if len(ans) > len(self.questions):
			error = out.ANSWERS_TOO_MANY.format(len(self.questions), len(ans))
			raise RuntimeError(error)			
		elif len(ans) < len(self.questions):
			error = out.ANSWERS_TOO_FEW.format(len(self.questions), len(ans))				
			raise RuntimeError(error)			

		for q, a in zip(self.questions, ans):			
			self.put_answer(q["q_id"], a)

	def put_answer(self, q_id, a):
		"""
			Answer a survey question
			========================
			q_id - question id
			a    - answer to question q_id (i.e., the index to the choices associated to this question)
		"""		
		
		choices = self.answer_choices[q_id]
		if a not in range(len(choices)):
			error = out.ANSWERS_BAD_CHOICE.format(q_id)
			raise RuntimeError(error)
		else:
			self.answers[q_id] = choices[a]		
	
	def put_notes(self, notes):
		"""
			Add a note to this survey
			=========================
			note - a text note
		"""
		self.notes = notes

	def is_complete(self):
		return len(self.questions) == len(self.answers)

	def has_open_notes(self):
		return self.notes is not None

	def get_answers(self):
		answers = {}
		#convert answers to their corresponding indices
		for q_id, ans in self.answers.items():
			answers[q_id] = self.answer_choices[q_id].index(ans)
		if self.notes is not None:
			answers["notes"] = self.notes
		#record timestamp
		ts = datetime.now().strftime('%Y-%m-%d %H:%M')
		answers["ts"]=ts
		return answers
		

class User(object):	

	def __init__(self, user_id, username, sleek):		
		self.username = username
		self.user_id = user_id		
		self.sleek = sleek
		my_surveys = self.sleek.backend.list_surveys(user_id)
		#dictionary {survey_id: (am_reminder, pm_reminder)}
		self.surveys = {s[1]:[s[2],s[3]] for s in my_surveys}		
	
	def survey_delete(self, survey_id):
		"""
			delete answers to survey survey_id
		"""
		self.sleek.backend.delete_answers(self.user_id, survey_id)		

	def survey_join(self, survey_id):
		"""
			join survey survey_id
		"""
		self.sleek.backend.join_survey(self.user_id, survey_id)		
		self.surveys[survey_id] = [None, None]
	
	def survey_leave(self, survey_id):
		"""
			leave survey survey_id and remove reminders
		"""		
		
		self.sleek.backend.leave_survey(self.user_id, survey_id)
		self.sleek.backend.save_reminder(self.user_id, survey_id, None)		
		#unset reminder in sleek
		self.sleek.set_reminder(self.user_id, survey_id, None)		
		del self.surveys[survey_id]

	def reminder_save(self, survey_id, am_reminder=None, pm_reminder=None):
		"""
			save and set reminders for survey survey_id
		"""				
		if am_reminder is not None:			
			self.sleek.backend.save_reminder(self.user_id, survey_id, am_reminder)				
			self.sleek.set_reminder(self.user_id, survey_id, am_reminder)
			self.surveys[survey_id][0] = am_reminder
		
		if pm_reminder is not None:			
			self.sleek.backend.save_reminder(self.user_id, survey_id, pm_reminder)
			self.sleek.set_reminder(self.user_id, survey_id, pm_reminder)				
			self.surveys[survey_id][1] = pm_reminder
	
class Sleek(ChatBot):

	sleek_announce = ''' I am {}, the chat bot :robot_face: -- \\
	                     If we never met, you can start by typing `help` '''	
	help_dict={
		"delete": ["`delete` `<SURVEY_ID>` | `all`", 
		           "delete all the answers to survey `<SURVEY_ID>` (or all)"],
		"join": ["`join` `<SURVEY_ID>` `[HH:MM (AM|PM)]`", 
				 "join survey `<SURVEY_ID>` and (optionally) set reminders: e.g., _join stress 9:00AM 2:00PM_"], 
		"leave": [ "`leave` `<SURVEY_ID>`",
		           "leave survey `<SURVEY_ID>`"],
		"list": ["`list`", " see a list of surveys"],
		"report": ["`report` `<SURVEY_ID>`",
		           "see previous answers to survey `<SURVEY_ID>`"],		
		"survey": ["`survey` `<SURVEY_ID>`", 
					"take survey `<SURVEY_ID>`"],
		"reminder": ["`reminder` `<SURVEY_ID>` `HH:MM (AM|PM)`",
					 "set reminders for survey `<SURVEY_ID>`"]	
		}	
	
	default_cfg = { "announce": sleek_announce,				
				    "help": "\n".join([" - ".join(h) for h in help_dict.values()])
				  }

	def __init__(self, confs, init_db=False):

		ChatBot.__init__(self, Sleek.default_cfg)		
		if confs["backend_type"]=="local":
			self.backend = Backend(confs, init=init_db)
		elif confs["backend_type"]=="kafka":
			self.backend = KafkaBackend(confs, init=init_db)		
		else:
			raise NotImplementedError
		 
		self.all_surveys = {x[0]:json.loads(x[1]) for x in self.backend.list_surveys()}
		self.reminders = defaultdict(dict)
		self.users = None				
		self.interactive = False
		self.bot_name = "silvio"
		self.scheduler = BackgroundScheduler()
		self.scheduler.start()
		#holds ongoing surveys
		self.ongoing_surveys = {}
		

	def load_users(self, users):
		"""
			Load Users
			##########
			users - dictionary {user_id:User}			
		"""			
		self.users = {uid: User(uid, uname, self) for uname, uid in users.items()}		

	#################################################################
	# BOT COMMAND METHODS
	#################################################################		

	def cmd_reminder_add(self, tokens, context):
		"""	
			Add a reminder for user/survey
			==============================
			user_id   - user id
			survey_id - survey id
		"""
		
		if len(tokens) < 3: 			
			return [self.oops(), out.MISSING_PARAMS, Sleek.help_dict["reminder"][0]]
		survey_id = tokens[1]	
		user_id = context["user_id"]	
		#check if survey exists
		if not survey_id in self.all_surveys: 				
			return [self.oops(), out.SURVEY_UNKNOWN.format(survey_id.upper())]
		try:
			am_reminder, pm_reminder = self.parse_reminders(tokens[2:])
		except ValueError as e:
			return [self.oops(), e.message]
		
		self.users[user_id].reminder_save(survey_id, am_reminder, pm_reminder)		
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

	def cmd_responses_show(self, tokens, context):		
	
		if len(tokens) < 2: 	
			return [self.oops(), out.MISSING_PARAMS, Sleek.help_dict["report"][0]]					
		
		survey_id = tokens[1]
		user_id = context["user_id"]											
		#check if survey exists
		if not survey_id in self.all_surveys: 				
			return [self.oops(), out.SURVEY_UNKNOWN.format(survey_id.upper())]

		if survey_id not in self.users[user_id].surveys: 				
			return [self.oops(), out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper())]

		
		r = self.backend.get_report(user_id, survey_id)		

		if len(r) > 0:
			report = display.report(self.all_surveys[survey_id], r)
			ret = [self.ack()]					
			ret.append(report)
			n = self.backend.get_notes(user_id, survey_id)	
			if len(n) > 0:
				notes = display.notes(survey_id, n)
				ret.append(notes)
		else:
			ret = [self.oops(), out.REPORT_EMPTY.format(survey_id.upper())]
		return ret

	def cmd_responses_delete(self, tokens, context):
		"""
			Delete answers to a survey
			=========================
			user_id   - user id
			survey_id - survey id
		"""	
		if len(tokens) < 2: 			
			return [self.oops(), out.MISSING_PARAMS, Sleek.help_dict["delete"][0]]					
		
		survey_id = tokens[1]
		user_id = context["user_id"]									
		if not survey_id in self.all_surveys: 				
			return [self.oops(), out.SURVEY_UNKNOWN.format(survey_id.upper())]
		
		if not survey_id in self.users[user_id].surveys:
			return [self.oops(),
					out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper(), self.bot_name)]
					
		try:		
			self.backend.delete_answers(user_id, survey_id)					
			return [self.ack(), out.ANSWERS_DELETE_OK.format(survey_id.upper())]			
		except RuntimeError as r:		
			e  = out.ANSWERS_DELETE_FAIL.format(survey_id.upper())
			e += "\n[err: {}]".format(str(r))		
			return [self.oops(), e]
				
	def cmd_survey_join(self, tokens, context):
		"""	
			Join a survey
			=============		
		"""		
		if len(tokens) < 3: 	
			return [self.oops(), out.MISSING_PARAMS, Sleek.help_dict["join"][0]]					
		
		survey_id = tokens[1]
		user_id = context["user_id"]											
		#check if survey exists
		if not survey_id in self.all_surveys: 				
			return [self.oops(), out.SURVEY_UNKNOWN.format(survey_id.upper())]

		if survey_id in self.users[user_id].surveys: 				
			return [self.oops(), out.SURVEY_IS_SUBSCRIBED.format(survey_id.upper())]

		#first validate reminder schedules
		try:			
			am_reminder, pm_reminder = self.parse_reminders(tokens[2:])			
		except ValueError as e:
			return [self.oops(), e.message]
		#join survey
		try:
			self.users[user_id].survey_join(survey_id)
			#try to set reminders
			if am_reminder is not None or pm_reminder is not None:
				rm = self.cmd_reminder_add(tokens, context)			
			return [self.ack(), out.SURVEY_JOIN_OK.format(survey_id.upper()), rm[1]]
		except RuntimeError as r:		
			e  = out.SURVEY_JOIN_FAIL.format(survey_id.upper())
			e += "\n[err: {}]".format(str(r))		
			return [self.oops(), e]

	def cmd_survey_leave(self, tokens, context):
		"""	
			Leave a survey
			=============
			user_id   - user id
			survey_id - survey id
		"""
		if len(tokens) < 2: 			
			return [self.oops(), out.MISSING_PARAMS, Sleek.help_dict["leave"][0]]					
		
		survey_id = tokens[1]
		user_id = context["user_id"]									
		if not survey_id in self.all_surveys: 				
			return [self.oops(), out.SURVEY_UNKNOWN.format(survey_id.upper())]
		
		if not survey_id in self.users[user_id].surveys:
			return [self.oops(),
					out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper(), self.bot_name)]

		try:		
			self.users[user_id].survey_leave(survey_id)				
			return [self.ack(), out.SURVEY_LEAVE_OK.format(survey_id.upper())]			
		except RuntimeError as r:		
			e  = out.SURVEY_LEAVE_FAIL.format(survey_id.upper())
			e += "\n[err: {}]".format(str(r))		
			return [self.oops(), e]
		
	def cmd_survey_list(self, tokens, context):
		"""	
			List user surveys
			=============			
		"""
		user_id = context["user_id"]
		user_surveys = self.users[user_id].surveys
		other_surveys = list(set(self.all_surveys.keys()) - set(user_surveys))		
		output = display.survey_list(user_surveys, other_surveys)
		return [self.ack(), output]

	def cmd_survey_take(self, tokens, context):
		if len(tokens) < 2: 			
			return [self.oops(), out.MISSING_PARAMS, Sleek.help_dict["leave"][0]]					
		
		survey_id = tokens[1]
		user_id = context["user_id"]
		channel = context["channel"]									
		if not survey_id in self.all_surveys: 				
			return [self.oops(), out.SURVEY_UNKNOWN.format(survey_id.upper())]

		if not survey_id in self.users[user_id].surveys:
			return [self.oops(),
					out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper(), self.bot_name)]
		#register new survey		
		s = self.all_surveys[survey_id]
		self.ongoing_surveys[channel] = Survey(s, user_id)
		return [self.ack(), display.survey(s)]

	def read(self, text, context):				
		tokens = text.split()
		#ongoing survey
		if context["channel"] in self.ongoing_surveys:
			return self.run_survey(tokens, context)
		else:			
			action = tokens[0]
			params =  u','.join(tokens[1:])		
			print u"[user: {}| action: {}({})]".format(context["user_id"], 
													   action, params)								
			#Actions
			# ---- DELETE DATA ----
			if action == "delete": return self.cmd_responses_delete(tokens, context)			
			
			# ---- SURVEY JOIN ----
			elif action == "join": return self.cmd_survey_join(tokens, context)			

			# ---- SURVEY TAKE ----
			elif action == "survey": return self.cmd_survey_take(tokens, context)			
				
			# ---- SURVEY LEAVE ----
			elif action == "leave": return self.cmd_survey_leave(tokens, context)			
				
			# ---- SURVEY LIST ----
			elif action == "list": return self.cmd_survey_list(tokens, context)			

			# ---- SHOW REPORT ----
			elif action == "report": return self.cmd_responses_show(tokens, context)
			# 	return "OK"
			
			#---- SCHEDULE SURVEY ----
			elif action == "reminder": return self.cmd_reminder_add(tokens, context)

			#---- PASS IT TO THE PARENT CLASS (maybe it knows how to handle this input)
			else: return ChatBot.chat(self, tokens, context)		
	
	def run_survey(self, tokens, context):		
		user_id = context["user_id"]
		channel = context["channel"]
		survey = self.ongoing_surveys[channel]
		assert survey.user_id == user_id
		
		if tokens[0] == "cancel":
			#remove this survey from the open surveys
			del self.ongoing_surveys[channel]
			return [self.ack(), out.SURVEY_CANCELED]

		elif tokens[0] == "notes":
			if not survey.has_open_notes():
				#empty note
				survey.put_notes("")
				return [out.ANSWERS_ADD_NOTE]
		
		elif tokens[0] == "ok":
			if not survey.is_complete():
				return [self.oops(), out.ANSWERS_INVALID]
			answers = survey.get_answers()			
			try:
				self.backend.save_answer(user_id, survey.id, answers)
				#remove this survey from the open surveys
				del self.ongoing_surveys[channel]
				return [self.ack(), out.ANSWERS_SAVE_OK]
			except ValueError:
				return [self.oops(), out.ANSWERS_SAVE_FAIL]
		
		#if a note was started, then this is a new note
		if survey.has_open_notes():
			survey.put_notes(" ".join(tokens))		
		else:
			#parse a new answer
			try:
				survey.put_answers(tokens)			
			except RuntimeError as e:
				return [self.oops(), e.message]

		ans = display.answer(survey.answers, survey.notes)
		if survey.notes is None:
			resp = out.ANSWERS_CONFIRM
		else:
			resp = out.NOTE_CONFIRM
		return [ans, resp]

	#################################################################
	# AUX METHODS
	#################################################################		

	def set_reminder(self, user_id, survey_id, schedule):
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

	def parse_reminders(self, tokens):
		am_reminder,pm_reminder = None, None
		#validate input times by trying to convert to datetime
		for t in tokens:	
			try:
				dt = datetime.strptime(t , '%I:%M%p').time()
				if   "am" in t: am_reminder = dt
				elif "pm" in t: pm_reminder = dt
			except ValueError:		
				raise ValueError(out.INVALID_TIME.format(t))
		#convert back to strings 
		if am_reminder is not None: am_reminder = am_reminder.strftime('%I:%M%p')
		if pm_reminder is not None: pm_reminder = pm_reminder.strftime('%I:%M%p')

		return am_reminder, pm_reminder	
