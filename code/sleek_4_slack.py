from collections import deque, defaultdict
from datetime import datetime
from ipdb import set_trace
import json
import pprint
import pandas as pd
from slackclient import SlackClient
import sqlite_backend as backend
from sleek import Sleek
import status
import time
from random import randint

READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose


def colstr(string, color):
    # set_trace()
    if color is None:
        cstring = string
    elif color == 'red':
        cstring = "\033[31m" + string  + "\033[0m"
    elif color == 'green':    
        cstring = "\033[32m" + string  + "\033[0m"

    return cstring    

class Sleek4Slack(Sleek):
	sleek_announce = ''' I am Sleek4Slack, the chat bot :robot_face: -- If we never met, you can start by typing `help`
*Note*: I only respond to commands directed @ me '''	
	
	sleek_help = '''  This a list of the commands I understand:				      
>>> 
- `delete` `<SURVEY_ID>` | `all` : delete all the answers to survey `<SURVEY_ID>` (or all)
- `join` `<SURVEY_ID>` `[HH:MM (AM|PM)]` `[HH:MM (AM|PM)]` join survey:  `<SURVEY_ID>` and (optionally) set reminders: e.g., _join stress 9:00AM 2:00PM_ 
- `leave` `<SURVEY_ID>`: to leave survey `<SURVEY_ID>`
- `list`: see a list of surveys
- `report` `<SURVEY_ID>`: to see a report with all the answers to survey `<SURVEY_ID>`
- `survey` `<SURVEY_ID>`: answer to survey `<SURVEY_ID>`

'''
#- `pause/resume`: pause/resume data collection
#- `upload`: to upload a new survey 
#- `remind` <survey_id>: set a reminder for survey <survey_id>
	default_cfg={
				"announce": sleek_announce,				
				"help": sleek_help,
				"nack": ["sorry, I didn't get that", "I don't understand that command","!?"]
				}

	def __init__(self, DB_path, init_backend=False, cfg=default_cfg):
		if init_backend:
			backend.init(DB_path)
			print "[created backend @ {}]".format(DB_path)		
		Sleek.__init__(self, cfg)
		self.DB_path = DB_path		
		self.users = {x[0]:"" for x in backend.get_users(self.DB_path)}
		#{survey_id:survey}
		self.current_surveys = {}	
		#{thread_id:(user_id, survey_id, response)}
		self.survey_threads = {}				
		self.slack_client = None
		self.bot_id = None	

	###### ------ PRIVATE METHODS		

	def __display_answer(self, a):		
		#del a["ts"]
		#del a["user_id"]
		ans = "\n".join(["*{}*: {}".format(f,v) for f,v in a.items()])
		out = "Your answers\n>>>{}".format(ans)
		return out
		

	def __display_survey(self, survey):
		out = "*===== _{}_ survey =====* \n".format(survey["survey_id"].upper())
		qst = "> *{}*: _{}_\n{}"		
		opt = "`{}`   {}"		
		for i,q in enumerate(survey["survey"]):			
			choices = "\n".join([opt.format(e,c) for e,c in enumerate(q["choices"])])
			out+= qst.format(q["id"], q["question"], choices)
			out+="\n\n"
		out += "*====================*"
		return out		

	def __display_report(self, survey_id, report):
		
		out = "*report _{}_*\n\n```{}```"
		s = self.current_surveys[survey_id]["survey"]

		df = pd.DataFrame(report).iloc[:,2:]
		df.columns = ["ts"] + [q["id"] for q in s]		
		df['ts'] = pd.to_datetime(df['ts'], unit='s')
		df.set_index('ts', inplace=True)	
		
		return out.format(survey_id.upper(), repr(df))	

	def __display_list(self, sl):
		active=">*{}*"
		inactive="~{}~"
		x = [active.format(s) if a else inactive.format(s) for s, a in sl.items()]
		out = "*Your Surveys*\n{}"
		return out.format("\n".join(x))


	def __get_time(self, t, period):
		assert period in ["AM","PM"]
		try:
			assert period in t
			nt = str(datetime.strptime(t , '%I:%M%p').time())
			return nt, "OK"
		except ValueError:
			return None, "invalid {} time".format(period)
		except (IndexError, AssertionError):			
			return None, "{} time is missing".format(period)
	
	def __list_surveys(self, user_id):				
		us = backend.list_surveys(self.DB_path, user_id)	
		user_surveys  = {x[1]:None for x in us}				
		surveys = {s:True if s in user_surveys else False for s in self.current_surveys.keys()}				
		return surveys	

	def __retrieve_usernames(self):		
		resp = self.slack_client.api_call("users.list")		
		if resp.get('ok'):
			# retrieve all users
			members = resp.get('members')
			for m in members:
				if 'name' in m and m.get('id') in self.users:
					try:
						self.users[m.get('id')] = m.get('name')
					except KeyError:
						pass
		else:
			raise RuntimeError("Could not retrieve members list\n{}".format(resp))		

	def __retrieve_surveys(self):
		data = backend.list_surveys(self.DB_path)
		self.current_surveys = {x[0]:json.loads(x[1]) for x in data}

	###### ------ CORE METHODS
	def chat(self, text, context):
		user_id = context["user_id"]
		tokens = text.split()
		action = tokens[0]
		print "[user: {}| action: {}({})]".format(user_id, action, ','.join(tokens[1:]))				
		
		#Actions
		# ---- DELETE DATA ----
		if action == "delete":			
			if len(tokens) < 2: return status.MISSING_PARAMS			
			return self.delete_answers(tokens, context)			
		
		# ---- JOIN SURVEY ----
		elif action == "join":			
			if len(tokens) < 4: return status.MISSING_PARAMS
			return self.join_survey(tokens, context)

		# ---- LEAVE SURVEY ----
		elif action == "leave":	
			if len(tokens) < 2: return status.MISSING_PARAMS					
			return self.leave_survey(tokens, context)											

		# ---- LIST SURVEYS ----
		elif action == "list": 
			return self.list_surveys(tokens, context)						

		# ---- SHOW REPORT ----
		elif action == "report":					
			if len(tokens) < 2: return status.MISSING_PARAMS									
			return self.report(tokens, context)			
		
		# ---- SCHEDULE SURVEY ----
		elif action == "remind":	
			if len(tokens) < 4: return status.MISSING_PARAMS											
			return self.remind_survey(tokens, context)

		# ---- ANSWER SURVEY ----
		elif action == "survey":
			if len(tokens) < 2: return status.MISSING_PARAMS
			return self.get_survey(tokens, context)			

		# ---- UPLOAD SURVEY ----
		elif action == "upload":			
			return "Coming soon"
		# ---- PASS IT TO SLEEK (parent class)
		else:
			resp = Sleek.chat(self, tokens, context)
			return resp

	def connect(self, api_token, greet=False):
		self.slack_client = SlackClient(api_token)
		self.__retrieve_usernames()	
		self.__retrieve_surveys()
 		if greet: 
 			self.post_channel("#general", self.greet())
 			self.post_channel("#general", self.announce()) 			
		return self.slack_client.rtm_connect()

	def listen(self, bot_id, verbose=False, dbg=False):
		"""
			verbose == True, print all the events of type "message"
			dbg == True, allow unhandled exceptions
		"""
		hat_bot = "<@{}>".format(bot_id) 
		while True:		
			reply = None	
			for output in self.slack_client.rtm_read():		
				if output["type"] != "message" or 'bot_id' in output: continue
				if verbose and not 'bot_id' in output:
					print "DBG:\n"
					pprint.pprint(output)
					#set_trace()	
				try:
					text = output['text']
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
						reply = status.SURVEY_CANCELED
					elif tokens[0] == "ok":
						reply = self.save_answer(thread_ts, ts)
					elif tokens[0] == "notes":
						reply = "Soon you will be able to add a note to this response" 
					else:
			   			reply = self.get_answer(thread_ts, text)			   			
				#or messages directed at the bot						   	
				elif hat_bot in text:			   						
					#remove bot mention
			   		text = text.replace(hat_bot,"").strip()			   					   		
			   		if dbg:
			   			#debug mode lets unhandled exceptions explode
			   			reply = self.chat(text, context)			   			
		   			else:
		   				try:
			   				reply = self.chat(text, context)
		   				except Exception as e:	   					
		   					reply = "[FATAL ERROR: {}]".format(e)

		   		if reply is None: continue				   	
   				#a reply can be either a message or a list thereof
   				if type(reply) == list: 
   					for r in reply: self.post_channel(channel, r, thread_ts)
				else: 
					self.post_channel(channel, reply, thread_ts)				
				time.sleep(READ_WEBSOCKET_DELAY)

	###### ------ BOT ACTION METHODS
	def get_answer(self, survey_thread, text):

		open_user, open_survey, _ = self.survey_threads[survey_thread]

		questions = self.current_surveys[open_survey]["survey"]		
		#assumes responses are separated by white spaces		
		try:
			answers = [int(a) for a in text.split()]
		except ValueError:
			return status.ANSWERS_INVALID
		#incorrect number of answers
		if len(answers) != len(questions):
			return status.ANSWERS_INCORRECT_NUMBER.format(len(questions), len(answers))		
		response = {}
		for q, a in zip(questions, answers):
			q_id = q["id"]
			choices = q["choices"]
			if a not in range(len(choices)):
				return status.ANSWERS_BAD_CHOICE.format(q["id"])
			else:
				response[q_id] = choices[a]
		# set_trace()
		self.survey_threads[survey_thread] = (open_user, open_survey, response)		
		return [self.__display_answer(response), status.ANSWERS_CONFIRM]

	def save_answer(self, survey_thread, ts):
		user_id, survey_id, response  = self.survey_threads[survey_thread]
		if response is None:
			return status.ANSWERS_INVALID
		try:			
			del self.survey_threads[survey_thread]
			# set_trace()
			if not backend.save_response(self.DB_path, user_id, survey_id, ts, response):
				return status.ANSWERS_SAVE_FAIL			
		except RuntimeError:
			return status.ANSWERS_SAVE_FAIL		
		return status.ANSWERS_SAVE_OK

	def delete_answers(self, tokens, context):		
		user_id = context["user_id"]				
		survey_id = tokens[1]					
		r = backend.delete_answers(self.DB_path, user_id, survey_id)
		if r > 0: return status.ANSWERS_DELETE_OK.format(survey_id.upper())
		else:	  return status.ANSWERS_DELETE_FAIL.format(survey_id.upper())
	
	def get_survey(self, tokens, context):		
		user_id = context["user_id"]
		survey_id = tokens[1]
		user_surveys = self.__list_surveys(user_id)
		#check if survey exists
		if not survey_id in self.current_surveys: return status.SURVEY_UNKNOWN.format(survey_id.upper())
		#check that user subscribed to this survey
		if not user_surveys[survey_id]: 
			return status.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper()) + " " + status.PLEASE_SUBSCRIBE		
		#register this thread as an open survey
		self.survey_threads[context["thread_ts"]] = (user_id, survey_id, None)
		s = self.current_surveys[survey_id]
		return self.__display_survey(s)

	def join_survey(self, tokens, context):
		user_id = context["user_id"]				
		err = ""		
		survey_id = tokens[1]						
		#validate schedule
		am_check, err = self.__get_time(tokens[2], "AM")		
		if am_check is None: return err
		pm_check, err = self.__get_time(tokens[3], "PM")		
		if pm_check is None: return err		
		#check if survey exists
		if not survey_id in self.current_surveys: return status.SURVEY_UNKNOWN.format(survey_id.upper())
		#check if user already subscrided this survey
		try:
			if self.__list_surveys(user_id)[survey_id]:
				return status.SURVEY_IS_SUBSCRIBED.format(survey_id.upper())
		except KeyError: 
			pass
		try:				
			#if user already subscribed this survey but it is inactive, just set it 'active'
			if not backend.toggle_survey(self.DB_path, user_id, survey_id, active=True):
				#try to join survey					
				if not backend.join_survey(self.DB_path, user_id, survey_id, am_check, pm_check):
					return status.SURVEY_JOIN_FAIL.format(survey_id.upper())
		except RuntimeError as e:			
			return status.SURVEY_JOIN_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))
		return status.SURVEY_JOIN_OK.format(survey_id,am_check,pm_check)

	def leave_survey(self, tokens, context):
		user_id = context["user_id"]
		survey_id = tokens[1]		
		#check if survey exists
		if not survey_id in self.current_surveys: return status.SURVEY_UNKNOWN.format(survey_id.upper())
		#check if user already subscrided this survey
		try:
			if not self.__list_surveys(user_id)[survey_id]:
				return status.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper())
		except KeyError: 
			pass						
		if not backend.toggle_survey(self.DB_path, user_id, survey_id, active=False):
			return status.SURVEY_LEAVE_FAIL.format(survey_id.upper())
		
		return status.SURVEY_LEAVE_OK.format(survey_id.upper())

	def list_surveys(self, tokens, context):	
		s = self.__list_surveys(context["user_id"])
		return self.__display_list(s)

	def report(self, tokens, context):
		user_id = context["user_id"]
		survey_id = tokens[1]
		try:
			rep = backend.get_report(self.DB_path, user_id, survey_id)
			if len(rep) == 0:
				return status.REPORT_EMPTY.format(survey_id.upper())
			return self.__display_report(survey_id, rep)
		except RuntimeError as e:
			return status.REPORT_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))			 	

	def remind_survey(self, tokens, context):
		user_id = context["user_id"]				
		err = ""		
		survey_id = tokens[1]						
		#validate schedule
		am_check, err = self.__get_time(tokens[2], "AM")		
		if am_check is None: return err
		pm_check, err = self.__get_time(tokens[3], "PM")		
		if pm_check is None: return err				
		try:				
			backend.schedule_survey(self.DB_path, user_id, survey_id, am_check, pm_check)
		except RuntimeError as e:			
			return status.SURVEY_REMIND_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))
		return status.SURVEY_REMIND_OK.format(survey_id,am_check,pm_check)

	def upload_survey(self, survey):
		"""
			Create a survey
			survey: survey
		"""		
		try:
			backend.create_survey(self.DB_path, survey)			
			self.__retrieve_surveys()
			return True
		except RuntimeError:
			return False

	###### ------ SLACK API METHODS
	def post_channel(self, channel, message, ts=None):
		print "[posting:\"{}\" to channel {}]".format(message,channel)
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
		
		if not resp.get("ok"): print "\033[31m[error: {}]\033[0m".format(resp["error"])

	def post_IM(self, user, message):
		im_id = self.ims[self.users[user]]
		print "[posting:\"{}\" to user @{} (IM:{})]".format(message,user,im_id)
		print self.slack_client.api_call("chat.postMessage",
										 channel="{}".format(im_id),
										 as_user=True,
										 text=message)


	# def pause(self, tokens, context):		
	# 	user_id = context["user_id"]
	# 	backend.toggle_user(self.DB_path, user_id, active=False)
	# 	return ack

	# def resume(self, tokens, context):		
	# 	user_id = context["user_id"]		
	# 	try:
	# 		backend.toggle_user(self.DB_path, user_id, active=False)
	# 	except RuntimeError as e:
	# 		return False, str(e)
	# 	return True, "OK"