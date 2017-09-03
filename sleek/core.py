from apscheduler.schedulers.background import BackgroundScheduler
from collections import defaultdict
from datetime import datetime
from ipdb import set_trace
import json
import pandas as pd
from string import ascii_letters

#sleek
from backend import Backend, KafkaBackend
from bots import ChatBot
import out

class SleekMsg(object):
	def __init__(self, m, msg_type="text"):
		assert type(m) is unicode, set_trace()
		self.text = m
		self.type = msg_type
		self.store = {}

	def __str__(self):
		return unicode(self.text).encode('utf-8')
	
	def __unicode__(self):
		return self.text

	def set_field(self, field_name, value):
		self.store[field_name] = value

	def get_field(self, field_name):
		try:
			return self.store[field_name]
		except KeyError:
			return None

class Survey(object):

	def __init__(self, surv, user_id, sleek):		
		self.user_id = user_id
		self.surv = surv
		self.sleek = sleek
		self.id = surv["id"]		
		self.questions = surv["questions"]
		self.answer_choices = {q["q_id"]:q["choices"] for q in surv["questions"]}		
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
	
	def save(self):
		if not self.is_complete():				
			raise RuntimeError(out.ANSWERS_INVALID)
		answers = self.get_answers()			
		try:
			self.sleek.backend.save_answer(self.user_id, self.id, answers)
			#remove this survey from the open surveys
			del self.sleek.ongoing_surveys[self.user_id]
		except ValueError:			
			raise RuntimeError(out.ANSWERS_SAVE_FAIL)

	def get_SleekMsg(self):
		txt_survey = format_survey(self.surv)
		fancy_survey = SleekMsg(txt_survey, msg_type="survey")		
		fancy_survey.set_field("survey", self.surv)		
		fancy_survey.set_field("user_id", self.user_id)		
		return fancy_survey

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

	__sleek_announce = ''' I am {}, the chat bot :robot_face: -- If we never met, you can start by typing `help` '''	
	__help_dict={
		"delete": [u"`delete` `<SURVEY_ID>` | `all`", 
		           u"delete all the answers to survey `<SURVEY_ID>` (or all)"],
		"join": [u"`join` `<SURVEY_ID>` `[HH:MM (AM|PM)]`", 
				 u"join survey `<SURVEY_ID>` and (optionally) set reminders: e.g., _join stress 9:00AM 2:00PM_"], 
		"leave": [ u"`leave` `<SURVEY_ID>`",
		           u"leave survey `<SURVEY_ID>`"],
		"list": [u"`list`", u" see a list of surveys"],
		"report": [u"`report` `<SURVEY_ID>`",
		           u"see previous answers to survey `<SURVEY_ID>`"],		
		"survey": [u"`survey` `<SURVEY_ID>`", 
					u"take survey `<SURVEY_ID>`"],
		"reminder": [u"`reminder` `<SURVEY_ID>` `HH:MM (AM|PM)`",
					 u"set reminders for survey `<SURVEY_ID>`"]	
		}	
	
	__default_cfg = { "announce": unicode(__sleek_announce),
				    "help": u"\n".join([" - ".join(__h) 
				    	for __h in __help_dict.values()])
				  }

	def __init__(self, confs, reminder_callback):
		#init parent class
		ChatBot.__init__(self, Sleek.__default_cfg)
		if confs["backend_type"]=="local":
			self.backend = Backend(confs)
		elif confs["backend_type"]=="kafka":
			self.backend = KafkaBackend(confs)		
		else:
			raise NotImplementedError		
		self.remind_user = reminder_callback 
		self.all_surveys = {x[0]:json.loads(x[1]) \
							for x in self.backend.list_surveys()}
		self.users = None
		#holds ongoing surveys
		self.ongoing_surveys = {}
		#start reminders scheduler
		self.reminders = defaultdict(dict)
		self.scheduler = BackgroundScheduler()
		self.scheduler.start()		

	def load_users(self, users):
		"""
			Load Users
			
			users - dictionary {user_id:User}			
		"""			
		self.users = {uid: User(uid, uname, self) for uname, uid in users.items()}

	#################################################################
	# BOT COMMAND METHODS
	#################################################################		

	def cmd_answers_report(self, tokens, context):	
		#check params
		if len(tokens) < 2:
			return [SleekMsg(self.oops()),
			        SleekMsg(out.MISSING_PARAMS),
			        SleekMsg(Sleek.__help_dict["report"][0])]
		survey_id = tokens[1]
		user_id = context["user_id"]
		#check if survey exists
		if not survey_id in self.all_surveys:
			return [SleekMsg(self.oops()),
			        SleekMsg(out.SURVEY_UNKNOWN.format(survey_id.upper()))]
		#check if user has subscribed this survey
		if survey_id not in self.users[user_id].surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper()))]
		data = self.backend.get_report(user_id, survey_id)
		if len(data) > 0:
			# set_trace()
			report = format_report(self.all_surveys[survey_id], data)
			#build fancy message
			m = SleekMsg(report, msg_type="report")
			m.set_field("survey", self.all_surveys[survey_id])
			m.set_field("data", data)
			return [SleekMsg(self.ack()), m]
		else:
			return [SleekMsg(self.oops()),
				    SleekMsg(out.REPORT_EMPTY.format(survey_id.upper()))]

	def cmd_answers_delete(self, tokens, context):
		"""
			Delete answers to a survey
			
			user_id   - user id
			survey_id - survey id
		"""	
		#check params
		if len(tokens) < 2:
			return [SleekMsg(self.oops()),
			        SleekMsg(out.MISSING_PARAMS),
			        SleekMsg(Sleek.__help_dict["delete"][0])]
		survey_id = tokens[1]
		user_id = context["user_id"]
		#check if survey exists									
		if not survey_id in self.all_surveys:			
			return [SleekMsg(self.oops()),
			 		SleekMsg(out.SURVEY_UNKNOWN.format(survey_id.upper()))]
		#check if user has subscribed this survey
		if not survey_id in self.users[user_id].surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper()))]
		try:
			self.backend.delete_answers(user_id, survey_id)
			return [SleekMsg(self.ack()),
			        SleekMsg(out.ANSWERS_DELETE_OK.format(survey_id.upper()))]
		except RuntimeError as r:
			e  = out.ANSWERS_DELETE_FAIL.format(survey_id.upper())
			e += "\n[err: {}]".format(str(r))
			return [SleekMsg(self.oops()),
					SleekMsg(e)]
				
	def cmd_survey_join(self, tokens, context):
		"""	
			Join a survey
					
		"""		
		#check params
		if len(tokens) < 3: 	
			return [SleekMsg(self.oops()),
					SleekMsg(out.MISSING_PARAMS),
					SleekMsg(Sleek.__help_dict["join"][0])]
		survey_id = tokens[1]
		user_id = context["user_id"]					
		#check if survey exists
		if not survey_id in self.all_surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_UNKNOWN.format(survey_id.upper()))]
		#check if user has subscribed this survey
		if survey_id in self.users[user_id].surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_IS_SUBSCRIBED.format(survey_id.upper()))]
		#first validate reminder schedules
		try:
			am_reminder, pm_reminder = self.parse_reminder_times(tokens[2:])
		except ValueError as e:
			return [SleekMsg(self.oops()),
					SleekMsg(e.message)]
		#join survey
		try:
			self.users[user_id].survey_join(survey_id)
			#try to set reminders
			if am_reminder is not None or pm_reminder is not None:
				rm = self.cmd_reminder_add(tokens, context)
			return [SleekMsg(self.ack()), 
					SleekMsg(out.SURVEY_JOIN_OK.format(survey_id.upper())), 
					rm[1]]
		except RuntimeError as r:
			e  = out.SURVEY_JOIN_FAIL.format(survey_id.upper())
			e += "\n[err: {}]".format(str(r))
			return [SleekMsg(self.oops()),
					SleekMsg(e)]

	def cmd_survey_leave(self, tokens, context):
		"""	
			Leave a survey
			
			user_id   - user id
			survey_id - survey id
		"""
		#check params
		if len(tokens) < 2: 			
			return [SleekMsg(self.oops()),
					SleekMsg(out.MISSING_PARAMS),
					SleekMsg(Sleek.__help_dict["leave"][0])]
		survey_id = tokens[1]
		user_id = context["user_id"]
		#check if survey exists							
		if not survey_id in self.all_surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_UNKNOWN.format(survey_id.upper()))]
		#check if user has subscribed this survey
		if not survey_id in self.users[user_id].surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper()))]
		try:
			self.users[user_id].survey_leave(survey_id)
			return [SleekMsg(self.ack()), 
					SleekMsg(out.SURVEY_LEAVE_OK.format(survey_id.upper()))]
		except RuntimeError as r:
			e  = out.SURVEY_LEAVE_FAIL.format(survey_id.upper())
			e += "\n[err: {}]".format(str(r))
			return [SleekMsg(self.oops()),
				    SleekMsg(e)]
		
	def cmd_survey_list(self, tokens, context):
		"""	
			List user surveys
						
		"""
		user_id = context["user_id"]
		user_surveys = self.users[user_id].surveys
		other_surveys = list(set(self.all_surveys.keys()) - set(user_surveys))
		output = format_survey_list(user_surveys, other_surveys)
		#build rich message
		m = SleekMsg(output, msg_type="survey_list")
		m.set_field("user_surveys", user_surveys)
		m.set_field("other_surveys", other_surveys)
		return [SleekMsg(self.ack()), m]

	def cmd_survey_take(self, tokens, context):
		#check params
		if len(tokens) < 2: 			
			return [SleekMsg(self.oops()),
					SleekMsg(out.MISSING_PARAMS),
					SleekMsg(Sleek.__help_dict["leave"][0]) ]
		survey_id = tokens[1]
		user_id = context["user_id"]					
		#check if survey exists
		if not survey_id in self.all_surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_UNKNOWN.format(survey_id.upper()))]
		#check if user has subscribed this survey
		if not survey_id in self.users[user_id].surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper()))]
		#register new survey		
		survey = self.all_surveys[survey_id]
		s = Survey(survey, user_id, self)
		self.ongoing_surveys[user_id] = s
		msg = s.get_SleekMsg()		
		return [SleekMsg(self.ack()), msg]

	def cmd_reminder_add(self, tokens, context):
		"""	
			Add a reminder for user/survey
			
			user_id   - user id
			survey_id - survey id
		"""		
		#check params
		if len(tokens) < 3: 			
			return [SleekMsg(self.oops()),
					SleekMsg(out.MISSING_PARAMS),
			        SleekMsg(Sleek.__help_dict["reminder"][0]) ]
		survey_id = tokens[1]
		user_id = context["user_id"]
		#check if survey exists
		if not survey_id in self.all_surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_UNKNOWN.format(survey_id.upper()))]
		#check if user has subscribed this survey
		if not survey_id in self.users[user_id].surveys:
			return [SleekMsg(self.oops()),
					SleekMsg(out.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper()))]
		try:
			am_reminder, pm_reminder = self.parse_reminder_times(tokens[2:])
		except ValueError as e:
			return [SleekMsg(self.oops()), 
					SleekMsg(e.message)]
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
			return [SleekMsg(self.oops()), 
				    SleekMsg(out.REMINDER_FAIL.format(survey_id))]
		 
	 	return [SleekMsg(self.ack()),
	 		    SleekMsg(txt)]

	def read(self, text, context):
		tokens = text.split()
		#ongoing survey
		if context["user_id"] in self.ongoing_surveys:
			return self.run_survey(tokens, context)
		else:
			action = tokens[0]
			params =  u','.join(tokens[1:])
			print u"[user: {}| action: {}({})]".format(context["user_id"],
													   action, params)
			#Actions			
			# ====== ANSWERS ======
			# ---- DELETE
			if action == "delete": return self.cmd_answers_delete(tokens, context)
			# ---- REPORT ----
			elif action == "report": return self.cmd_answers_report(tokens, context)
			# ====== SURVEYS ======
			# ---- JOIN ----
			elif action == "join": return self.cmd_survey_join(tokens, context)
			# ---- TAKE ----
			elif action == "survey": return self.cmd_survey_take(tokens, context)
			# ---- LEAVE ----
			elif action == "leave": return self.cmd_survey_leave(tokens, context)
			# ---- LIST ----
			elif action == "list": return self.cmd_survey_list(tokens, context)		
			#---- REMIND ----
			elif action == "reminder": return self.cmd_reminder_add(tokens, context)
			#---- PASS IT TO THE PARENT CLASS (maybe it knows how to handle this input)
			else: 
				replies = ChatBot.chat(self, tokens, context)
				replies = [SleekMsg(reply) for reply in replies]
				return replies
	
	def run_survey(self, tokens, context):
		user_id = context["user_id"]
		survey = self.ongoing_surveys[user_id]
		assert survey.user_id == user_id
		if tokens[0] == "cancel":
			#remove this survey from the open surveys
			del self.ongoing_surveys[user_id]
			return [SleekMsg(self.ack()),
					SleekMsg(out.SURVEY_CANCELED)]
		elif tokens[0] == "notes":
			if not survey.has_open_notes():
				#empty note
				survey.put_notes("")
				return [SleekMsg(out.ANSWERS_ADD_NOTE)]
		elif tokens[0] == "ok":
			try:
				survey.save()
				return [SleekMsg(self.ack()),
						SleekMsg(out.ANSWERS_SAVE_OK)]
			except RuntimeError as e:
				return [SleekMsg(self.oops()), 
						SleekMsg(e.message)]
		# --- PARSE ANSWERS TO SURVEY ---
		#if a note was started, then this is a new note
		if survey.has_open_notes(): survey.put_notes(" ".join(tokens))
		else:
			#parse a new answer
			try:
				survey.put_answers(tokens)
			except RuntimeError as e:
				return [SleekMsg(e.message)]
		#show current answers
		ans = format_answer(survey.answers, survey.notes)
		#fancy message		
		fm = SleekMsg(ans, msg_type="answer")
		fm.set_field("answers", survey.answers)
		if survey.notes is None:
			resp = out.ANSWERS_CONFIRM
		else:
			fm.set_field("notes", survey.notes)
			resp = out.NOTE_CONFIRM
		return [fm, SleekMsg(resp)]

	#################################################################
	# REMINDER METHODS
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
																schedule)			
			remind_at = datetime.strptime(schedule , '%I:%M%p').time()
			period = remind_at.strftime('%p')			
			try:
				job = self.reminders[(user_id,survey_id)][period]
				#if this reminder already exists, simply update the schedule
				job.reschedule(trigger='cron', hour=remind_at.hour, 
							   minute=remind_at.minute)		
			except KeyError:
				#else, create new
				job = self.scheduler.add_job(self.remind_user,
											 args=[user_id,survey_id.upper(),
											 	  period.upper()],
											 	  trigger='cron',
											 	  hour=remind_at.hour,
											 	  minute=remind_at.minute)
				self.reminders[(user_id,survey_id)][period] = job

	def parse_reminder_times(self, tokens):
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

	#################################################################
	# OTHER METHODS
	#################################################################		
	def get_survey_answers(self, user_id):
		survey = self.ongoing_surveys[user_id]
		ans = format_answer(survey.answers, survey.notes)
		s = SleekMsg(ans, msg_type="answer")
		s.set_field("answers", survey.answers)
		s.set_field("notes", survey.notes)
		s.set_field("user_id", "user_id")
		return s

	def cancel_survey(self, user_id):
		#remove this survey from the open surveys
		del self.ongoing_surveys[user_id]

# methods to format the replies
def format_answer(a, notes=None):
	ans = u"\n".join(["*{}*: {}".format(f,v) for f,v in a.items() if f!="notes"])
	if notes is not None:
		ret = u"Your answers\n>>>{}\n\nnotes:\n{} ".format(ans,notes)
	else:
		ret = u"Your answers\n>>>{}".format(ans)
	return ret

def format_report(survey, data):
	survey_id = survey["id"]
	ret = u"*report {}*\n\n{}"	
	#survey answer tables have the columns: id, user_id, timestamp, answer_1, ... , answer_N, notes	
	df_answers = pd.DataFrame(data).iloc[:,2:]				
	df_answers.columns = ["ts"] + [q["q_id"] for q in survey["questions"]] + ["notes"]
	df_answers['ts'] = pd.to_datetime(df_answers['ts']).dt.strftime("%Y-%m-%d %H:%M")
	#convert numeric answers back to their text values
	for q in survey["questions"]:
		q_id = q["q_id"]
		choices = q["choices"]
		answers = df_answers[q_id]
		df_answers[q_id] = map(lambda x: choices[int(x)], answers)	
	#replace None with empty string in the notes	
	df_answers["notes"] = map(lambda x: "" if x is None else x, 
							  df_answers["notes"])

	df_answers.set_index('ts', inplace=True)	
	x = ret.format(survey_id.upper(), repr(df_answers))
	return x

def format_survey(survey):
	ret = u"*===== {} Survey =====* \n".format(survey["id"].upper())
	qst = u"> *{}*: {}\n{}"		
	opt = u"{})   {}"		
	for i,q in enumerate(survey["questions"]):			
		choices = u"\n".join([opt.format(ascii_letters[e],c) for e,c in enumerate(q["choices"])])
		ret+= qst.format(q["q_id"], q["question"], choices)
		ret+=u"\n\n"
	ret += u"*====================*"
	return ret		

def format_survey_list( user_surveys, other_surveys):
	active=u">*{}*\t [{}] \t [{}] "
	inactive=u">  - {}"
	us = [active.format(s,r[0],r[1]) for s, r in user_surveys.items()]
	ot = [inactive.format(s) for s in other_surveys]
	ret = u"*===== Your Surveys =====*\n*Subscribed*\n{}\n*Available*\n{}"
	return ret.format("\n".join(us),"\n".join(ot))