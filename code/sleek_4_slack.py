from collections import deque, defaultdict
from datetime import datetime
import status
from ipdb import set_trace
import pprint
import json
from slackclient import SlackClient
import sqlite_backend as backend
from sleek import Sleek
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
	sleek_announce = ''' Hello I am Sleek4Slack, the chat bot :) '''	
	
	sleek_help = ''' This a list of the commands I understand:				      
- delete <survey_id|all>: delete all the answers to survey <survey_id> (or all)
- join <survey_id> [HH:MM(AM|PM)] [HH:MM(AM|PM)] join survey <survey_id> and be reminded at HH:MM (AM) and at HH:MM (PM)
- leave <survey_id>: to leave survey <survey_id>
- pause/resume: pause/resume data collection
- list: see a list of surveys
- remind <survey_id>: to reschudle survey <survey_id>
- report <survey_id>: to see a report with all the answers to survey <survey_id>
- survey <survey_id>: answer to survey <survey_id>
- upload: to upload a new survey 
'''
	
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
		self.connected = False	
		self.surveys = {}	
		self.open_responses = defaultdict(dict)
		self.slack_client = None
		self.bot_id = None	

	###### ------ PRIVATE METHODS
	def _engage(self, user_id, survey_id):

		try:
			#(response_id, list_of_questions)
			response_id, questions = self.open_responses[user_id][survey_id]
		except KeyError:		
			# if there is no open response to this (user, survey) open a new one
			survey = self.surveys[survey_id]["survey"]
			#start new response					
			response_id = backend.new_response(self.DB_path, user_id, survey_id, int(time.time()))
			self.open_responses[user_id][survey_id] = (response_id, deque(survey))			
			return self._engage(user_id, survey_id)
		return questions[0], response_id

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
		
	def __retrieve_usernames(self):
		assert self.connected, "Could not retrieve members. Not connected"
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
		self.surveys = {x[0]:json.loads(x[1]) for x in data}

	###### ------ CORE METHODS
	def chat(self, text, context):
		user_id = context["user"]
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
			return self.engage(tokens, context)			

		# ---- UPLOAD SURVEY ----
		elif action == "upload":			
			return "Coming soon"
		# ---- PASS IT TO SLEEK (parent class)
		else:
			resp = Sleek.chat(self, tokens, context)
			return resp

	def connect(self, api_token, greet=False):
		self.slack_client = SlackClient(api_token)
		self.connected = True									
		self.__retrieve_usernames()	
		self.__retrieve_surveys()
 		if greet: self.post_channel("#general", self.greet())
		return self.slack_client.rtm_connect()

	def listen(self, bot_id, verbose=False, dbg=False):
		"""
			verbose == True, print all the events of type "message"
			dbg == True, allow unhandled exceptions
		"""
		bot_mentioned = "<@{}>".format(bot_id) 
		while True:
			time.sleep(READ_WEBSOCKET_DELAY)
			for output in self.slack_client.rtm_read():		
				if verbose and output["type"] == "message" and not 'bot_id' in output:
					print "DBG:\n"
					pprint.pprint(output)
						#set_trace()	
				try:
					text = output['text']
					ts = output['ts']
					channel = output['channel']
				   	user = output['user']		   	
				except KeyError:
					continue			
			   	#only react to messages directed at the bot						   	
				if bot_mentioned in text:			   		
				   	try: thread_ts = output['thread_ts']
			   		except KeyError: thread_ts = ts				   	
			   		#remove bot mention
			   		text = text.replace(bot_mentioned,"").strip()			   		
			   		if dbg:
			   			#debug mode lets unhandled exceptions explode
			   			reply = self.chat(text, {"user":user,"ts":ts,"channel":channel})			   			
		   			else:
		   				try:
			   				reply = self.chat(text, {"user":user,"ts":ts,"channel":channel})
		   				except Exception as e:	   					
		   					reply = "[FATAL ERROR: {}]".format(e)				   	
	   				if type(reply) == list: 
	   					for r in reply: self.post_channel(channel, r, thread_ts)
   					else: 
   						self.post_channel(channel, reply, thread_ts)

	###### ------ BOT ACTION METHODS
	def answer(self, user_id, survey_id, question_id, response_id, response):
		resp_id, questions = self.open_responses[user_id][survey_id]
		q = questions.popleft()
		choices = q["choices"]
		assert q["id"] == question_id, set_trace()
		assert resp_id == response_id, set_trace()
		#reject bad input
		if response not in choices: return False						
		backend.save_response(self.DB_path, survey_id, user_id, response_id, {question_id:response})
		#if this is the last question close the response
		if len(questions)==0:
			print "[closing response: {}]".format(response_id)
			backend.close_response(self.DB_path, user_id, survey_id, response_id)
		return True

	def delete_answers(self, tokens, context):		
		user_id = context["user"]				
		survey_id = tokens[1]					
		r = backend.delete_answers(self.DB_path, user_id, survey_id)
		if r > 0: return status.DELETE_ANSWERS_OK.format(survey_id.upper())
		else:	  return status.DELETE_ANSWERS_FAIL.format(survey_id.upper())
	
	def delete_survey(self, survey_id):
		"""
			Delete a survey
			survey_id: survey id
		"""		
		backend.delete_survey(self.DB_path, survey_id)

	def engage(self, tokens, context):
		user_id = context["user"]						
		survey_id = tokens[1]
		user_surveys = self.list_surveys(tokens, context)
		if not user_surveys[survey_id]: 
			return status.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper())
		else:
			return self._engage(user_id, survey_id)		

	def join_survey(self, tokens, context):
		user_id = context["user"]				
		err = ""		
		survey_id = tokens[1]						
		#validate schedule
		am_check, err = self.__get_time(tokens[2], "AM")		
		if am_check is None: return err
		pm_check, err = self.__get_time(tokens[3], "PM")		
		if pm_check is None: return err		
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
					return status.JOIN_SURVEY_FAIL.format(survey_id.upper())
		except RuntimeError as e:			
			return status.JOIN_SURVEY_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))
		return status.JOIN_SURVEY_OK.format(survey_id,am_check,pm_check)

	def leave_survey(self, tokens, context):				
		user_id = context["user"]
		survey_id = tokens[1]		
		#check if user already subscrided this survey
		try:
			if not self.__list_surveys(user_id)[survey_id]:
				return status.SURVEY_NOT_SUBSCRIBED.format(survey_id.upper())
		except KeyError: 
			pass						
		if backend.toggle_survey(self.DB_path, user_id, survey_id, active=False):
			return status.LEAVE_SURVEY_OK.format(survey_id.upper())
		else: 
			return status.LEAVE_SURVEY_FAIL.format(survey_id.upper())

	def __list_surveys(self, user_id):				
		us = backend.list_surveys(self.DB_path, user_id)	
		user_surveys  = {x[1]:None for x in us}				
		surveys = {s:True if s in user_surveys else False for s in self.surveys.keys()}				
		return surveys	

	def list_surveys(self, tokens, context):	
		return self.__list_surveys(context["user"])

	def report(self, tokens, context):
		user_id = context["user"]
		survey_id = tokens[1]
		try:
			return backend.get_report(self.DB_path, user_id, survey_id)
		except RuntimeError as e:
			return status.REPORT_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))			 	

	def remind_survey(self, tokens, context):
		user_id = context["user"]				
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
			return status.REMIND_SURVEY_FAIL.format(survey_id.upper()) + " [err: {}]".format(str(e))
		return status.REMIND_SURVEY_OK.format(survey_id,am_check,pm_check)

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
	# 	user_id = context["user"]
	# 	backend.toggle_user(self.DB_path, user_id, active=False)
	# 	return ack

	# def resume(self, tokens, context):		
	# 	user_id = context["user"]		
	# 	try:
	# 		backend.toggle_user(self.DB_path, user_id, active=False)
	# 	except RuntimeError as e:
	# 		return False, str(e)
	# 	return True, "OK"


# def schedule_survey(self, tokens, context):
	# 	user_id = context["user"]				
	# 	survey_id = tokens[1]					
	# 	err = ""
	# 	try:
	# 		assert "AM" in tokens[2] 			
	# 		am_check = str(datetime.strptime(tokens[2] , '%I:%M%p').time())
	# 	except ValueError:
	# 		err = "invalid AM time"
	# 	except (IndexError,AssertionError):
	# 		err = "AM time is missing"				
	# 	try:
	# 		assert "PM" in tokens[3] 			
	# 		pm_check = str(datetime.strptime(tokens[3] , '%I:%M%p').time())
	# 	except ValueError:
	# 		err = "invalid PM time"
	# 	except (IndexError,AssertionError):
	# 		err = "PM time is missing"		
		
	# 	if len(err)>0:
	# 		return False, err
	# 	else:
	# 		try:			
	# 			backend.schedule_survey(self.DB_path, user_id, survey_id, am_check, pm_check)
	# 		except RuntimeError as e:			
	# 			return False, str(e)
	# 	return True, "OK"

# def chat(self, tokens, context):

	# 	"""
	# 		parse input
	# 	"""
	# 	user_id = context["user"]
	# 	print "[tokens: {}| user: {}]".format(repr(tokens), user_id)		
	# 	#Actions

	# 	# ---- DELETE DATA ----
	# 	if tokens[0] == "delete":
	# 		#basic validation		
	# 		if len(tokens) < 2: return status.MISSING_PARAMS			
	# 		res, err = self.delete_answers(tokens, context)
	# 		if res:
	# 			return ack.format(tokens[1].upper())
	# 		else:
	# 			if err is not None:
	# 				return nack.format(tokens[1].upper()) + " [err:{}]".format(err)
	# 			else:
	# 				return nack.format(tokens[1].upper())
		
	# 	# ---- JOIN SURVEY ----
	# 	elif tokens[0] == "join":
	# 		#basic validation		
	# 		if len(tokens) < 4: return status.MISSING_PARAMS
	# 		#output
	# 		ack = "You joined survey {}. I will remind you to fill it at {} and then at {}"	
	# 		nack = "Could not join survey {}"
	# 		res, err = self.join_survey(tokens, context)
	# 		if res:
	# 			return ack.format(tokens[1].upper(),tokens[2],tokens[3])
	# 		else:
	# 			if err is not None:
	# 				return nack.format(tokens[1].upper()) + " [err:{}]".format(err)
	# 			else:
	# 				return nack.format(tokens[1].upper())

	# 	# ---- LEAVE SURVEY ----
	# 	elif tokens[0] == "leave":	
	# 		if len(tokens) < 2: return status.MISSING_PARAMS		
	# 		ack = "You left survey {}. I will keep your data and you can join this survey again anytime you want. If you want to delete all of your answers use the 'delete' command"	
	# 		nack = "Could not leave survey {}"
	# 		res, err  = self.leave_survey(tokens, context)								
	# 		if res:
	# 			return ack.format(tokens[1].upper())
	# 		else:
	# 			if err is not None:
	# 				return nack.format(tokens[1].upper()) + " [err:{}]".format(err)
	# 			else:
	# 				return nack.format(tokens[1].upper())

	# 	# ---- LIST SURVEYS ----
	# 	elif tokens[0] == "list": 
	# 		return self.list_surveys(tokens, context)						

	# 	# ---- SHOW REPORT ----
	# 	elif tokens[0] == "report":		
	# 		nack = "Could retrieve report for survey {}"
	# 		if len(tokens) < 2: return status.MISSING_PARAMS									
	# 		res, err = self.report(tokens, context)			
	# 		if err == "OK":
	# 			return res
	# 		else:
	# 			return nack.format(tokens[1]) + " [err:{}]".format(err)
		
	# 	# ---- SCHEDULE SURVEY ----
	# 	elif tokens[0] == "schedule":	
	# 		if len(tokens) < 4: return status.MISSING_PARAMS											
	# 		ack = "The schedule for survey {} was updated. I will remind you to take the survey at {} and again at {}"	
	# 		nack = "Could update schedule for survey {}"
	# 		res, err  = self.schedule(tokens, context)
	# 		if res:
	# 			return ack.format(tokens[1].upper())
	# 		else:
	# 			if len(err)>0: 
	# 				return nack.format(tokens[1].upper()) + " [err:{}]".format(err)
	# 			else:
	# 				return nack.format(tokens[1].upper())

	# 	# ---- ANSWER SURVEY ----
	# 	elif tokens[0] == "survey":
	# 		if len(tokens) < 2: return status.MISSING_PARAMS
	# 		x, err = self.engage(tokens, context)			
	# 		if x is None:
	# 			return err
	# 		else:				
	# 			return [self.ack(),x[0]]				
	# 	else:
	# 		resp = Sleek.chat(self, tokens, context)
	# 		return resp