import pandas as pd
from string import ascii_letters
#from ipdb import set_trace


COLOR_1="#0D6D8C"
COLOR_2="#00A0BF"
def format(msg):	
	if msg.type == "survey_list":
		user_surveys = msg.get_field("user_surveys")
		other_surveys = msg.get_field("other_surveys")
		return attach_survey_list(user_surveys, other_surveys)		 
	elif msg.type == "report":
		survey = msg.get_field("survey")
		data   = msg.get_field("data")
		return attach_report(survey, data, None)
	elif msg.type == "survey":
		survey = msg.get_field("survey")
		user_id = msg.get_field("user_id")
		api_token = msg.get_field("api_token")
		callback_id = user_id+"@"+api_token
		if msg.get_field("interactive"):
			attach = attach_survey(survey, callback_id)
			ok_button = msg.get_field("ok_button") == True
			notes_button = msg.get_field("notes_button") == True
			actions = get_actions(callback_id, 
								  cancel_button=True,
								  ok_button=ok_button, 
								  notes_button=notes_button)
			attach.append(actions)
			return attach
		else:
			return text_survey(survey)			
	elif msg.type == "answer":
		ans = msg.get_field("answers")
		notes = msg.get_field("notes")
		user_id = msg.get_field("user_id")
		return attach_answer(ans, user_id, notes=notes)
	else:	 
		return msg.text

def attach_answer(a, callback_id, notes=None):
	
	field_list = []
	for f,v in a.items():
		if f=="notes":continue		
		field_list.append({                    
                    "value": u"*{}*".format(f),
                    "short": True
                })
		field_list.append({                    
                    "value": u"_{}_".format(str(v).replace(">","+")),
                    "short": True
                })

	attach = [{ "fallback": "reponse",
        		 "color": COLOR_1,		        		          		 
        		 "pretext": "These were you responses",
        		 # u"title":"{} survey".format(survey_id.upper()),
        		 "callback_id":callback_id,
        	     "fields":field_list,
        	     "text":" ",        	     
        	     "mrkdwn_in": ["text","pretext","title","fields"]
		 				}]

	if notes is not None:
		attach.append({ "fallback": "notes",
        		 		"color": COLOR_2,	
        		 		"title": "notes",	        
        		 		"callback_id":callback_id,          		 
        		 		"text": u"_{}_".format(notes),        	     		
        	     		"mrkdwn_in": ["text","pretext","title","fields"]        	
		 				})

	return attach

def get_actions(callback_id, cancel_button=True, 
				ok_button=False, notes_button=False):
	actions = []
	if cancel_button:
		actions.append({"name": "action",
        				"text": "cancel",
        				"type": "button",		        
        				"value":"[sleek:cancel]", 
        				"style":"danger"})
	if notes_button:
		actions.append({"name": "action",
    					"text": "notes",
    					"type": "button",		        
    					"value":"[sleek:notes]"})
	if ok_button:
		actions.append({"name": "action",
    					"text": "ok",
    					"type": "button",	
    					"style": "primary",	        
    					"value":"[sleek:ok]"})	
	
	attach = { "fallback": "actions",
    		 	"color": "#CCCCCC",	        		 		
    		 	"callback_id":callback_id,          		         		 		
    	     	"mrkdwn_in": ["text","pretext","title","fields"],
    	     	"actions":actions }
 	return attach

def attach_report(survey, data, notes):	

	survey_id = survey["id"]	
	df_answers = pd.DataFrame(data).iloc[:,2:]
	# df_answers.columns =  ["ts"]
	# df_answers.columns += [q["q_id"] for q in survey["questions"]] 
	# df_answers.columns += ["notes"]
	df_answers.columns = ["ts"] + [q["q_id"] for q in survey["questions"]] + ["notes"]
	df_answers['ts'] = pd.to_datetime(df_answers['ts']).dt.strftime("%Y-%m-%d %H:%M")
	#convert numeric answers back to their text values
	for q in survey["questions"]:
		q_id = q["q_id"]
		choices = q["choices"]
		answers = df_answers[q_id]
		df_answers[q_id] = map(lambda x: choices[int(x)], answers)	
	#replace None with empty string in the notes
	df_answers["notes"] = map(lambda x: "" if x is None else x, df_answers["notes"])	
	df_answers.set_index('ts', inplace=True)	
	report = "```{}```".format(repr(df_answers))
	attach = [
    			{ "fallback": "Survey Report",
        		  "color": COLOR_1,
        		  "pretext": u"Here is your report",            
        		  "title": survey_id.title(),            
        	      "text": report,
        	      "mrkdwn_in": ["text","pretext","title"] },    	        
			]

	return attach

def attach_survey(survey, callback_id):
	attaches = []	

	for q_num, q in enumerate(survey["questions"]):			
		pq = map(lambda x:"{}".format(x) if x!="\n" else "\n", q["question"].split())
		pretty_question = " ".join(pq)
		pretty_question = q["question"]
		question = [{                    
                    "value": u"*{}*: {}".format(q["q_id"], pretty_question),
                    "short": False
                }]		
		actions = []
		for e,c in enumerate(q["choices"]):
			actions.append({
		                    "name": q["q_id"],
		                    "text": u"{}".format(c),
		                    "type": "button",
		                    "value":e
			                })			

		x = { "fallback": "Survey",
    		   "color": COLOR_1,    		   
    	        "fields": question,
           		"callback_id": callback_id,
	            "actions": actions,
    	       "mrkdwn_in": ["text","pretext","title","fields","buttons","actions"] 
    	      }
		attaches.append(x)		
	return attaches	

def attach_survey_list(user_surveys, other_surveys):	
	active_list = []
	attach = []	
	if len(user_surveys) > 0:
		active_list.append({                    
	                    "value": "*Subscribed Surveys*",
	                    "short": True
	                })
			
		active_list.append({                    
	                "value": "*Reminders*",
	                "short": True
	            })
		for survey, reminders in user_surveys.items():		
			#format reminder schedules
			rems = ""
			for r in reminders: 
				if r is not None:
					rems+="`{}`\t".format(r)
			#if this survey has reminders put survey and reminders side by side
			if len(rems)>0:
				active_list.append({                    
	                    "value": u">*{}*".format(survey),
	                    "short": True
	                })
			
				active_list.append({                    
		                    "value": "{}".format(rems),
		                    "short": True
		                })
			else:
				active_list.append({                    
	                    "value": u">*{}*".format(survey),
	                    "short": False
	                })

		#build attach
		attach.append({ "fallback": "reponse",
	        		 "color": COLOR_1,  
	        		 "title": "",
	        	     "fields":active_list,
	        	     "mrkdwn_in": ["text","pretext","title","fields"]
			 				})
	inactive_list = []
	for survey in other_surveys:
		inactive_list.append({                    
                    "value": u"_{}_".format(survey),
                    "short": True
                })
		
	attach.append({ "fallback": "reponse",
    		 		"color": COLOR_2,
    		 		"title": "Available Surveys",
    	     		"fields":inactive_list,
    	     		"mrkdwn_in": ["text","pretext","title","fields"]})
   	return attach
	
# methods to format the replies
def text_answer(a, notes=None):	
	
	ans = u"\n".join(["*{}*: {}".format(f,v) for f,v in a.items() if f!="notes"])
	if notes is not None:
		ret = u"Your answers\n>>>{}\n_notes_:```{}```".format(ans,notes)
	else:
		ret = u"Your answers\n>>>{}".format(ans)
	return ret

def text_notes(survey_id, notes):
	ret = u"*notes _{}_*\n\n```{}```"		
	df = pd.DataFrame(notes)
	df.columns = ["ts","notes"]
	df['ts'] = pd.to_datetime(df['ts']).dt.strftime("%Y-%m-%d %H:%M")
	df.set_index('ts', inplace=True)			
	return ret.format(survey_id.upper(), repr(df))	

def text_report(survey, data):
	survey_id = survey["id"]
	ret = u"*report _{}_*\n\n```{}```"	
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
	df_answers["notes"] = map(lambda x: "" if x is None else x, df_answers["notes"])	
	df_answers.set_index('ts', inplace=True)	
	return ret.format(survey_id.upper(), repr(df_answers))	

def text_survey(survey):
	ret = u"*===== _{}_ survey =====* \n".format(survey["id"].upper())
	qst = u"> *{}*: _{}_\n{}"		
	opt = u"`{}`   {}"		
	for i,q in enumerate(survey["questions"]):			
		choices = u"\n".join([opt.format(ascii_letters[e],c) for e,c in enumerate(q["choices"])])
		ret+= qst.format(q["q_id"], q["question"], choices)
		ret+=u"\n\n"
	ret += u"*====================*"
	return ret		

def text_survey_list( user_surveys, other_surveys):
	active=u">*{}*\t`{}`\t`{}`"
	inactive=u"~{}~"
	us = [active.format(s,r[0],r[1]) for s, r in user_surveys.items()]
	ot = [inactive.format(s) for s in other_surveys]
	display = u"*Your Surveys*\n{}\n{}"
	return display.format("\n".join(us),"\n".join(ot))



