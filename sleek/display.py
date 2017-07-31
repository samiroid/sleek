import pandas as pd
from string import ascii_letters
import out
from ipdb import set_trace
import pprint

test_attach = [
        {
            "fallback": "Required plain-text summary of the attachment.",
            "color": "#36a64f",
            "pretext": "Optional text that appears above the attachment block",
            "author_name": "Bobby Tables",
            "author_link": "http://flickr.com/bobby/",
            "author_icon": "http://flickr.com/icons/bobby.jpg",
            "title": "Slack API Documentation",
            "title_link": "https://api.slack.com/",
            "text": "Optional text that appears within the attachment",
            "fields": [
                {
                    "title": "Priority",
                    "value": "High",
                    "short": False
                }
            ],
            "image_url": "http://my-website.com/path/to/image.jpg",
            "thumb_url": "http://example.com/path/to/thumb.png",
            "footer": "Slack API",
            "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
            "ts": 123456789
        }
    ]



# methods to format the replies
def answer(a):
	notes = None
	if "notes" in a: notes = a["notes"]			
	ans = u"\n".join(["*{}*: {}".format(f,v) for f,v in a.items() if f!="notes"])
	if notes is not None:
		ret = u"Your answers\n>>>{}\n_notes_:```{}```".format(ans,notes)
	else:
		ret = u"Your answers\n>>>{}".format(ans)
	return ret

def notes( survey_id, notes):
	ret = u"*notes _{}_*\n\n```{}```"		
	df = pd.DataFrame(notes)
	df.columns = ["ts","notes"]
	df['ts'] = pd.to_datetime(df['ts']).dt.strftime("%Y-%m-%d %H:%M")
	df.set_index('ts', inplace=True)			
	return ret.format(survey_id.upper(), repr(df))	

def report(survey, data):
	survey_id = survey["id"]
	ret = u"*report _{}_*\n\n```{}```"
	#survey = current_surveys[survey_id]["questions"]
	#survey answer tables have the columns: id, user_id, timestamp, answer_1, ... , answer_N, notes
	#keeping only: ts, timestamp, answer_1, ... , answer_N
	df = pd.DataFrame(data).iloc[:,2:-1]		
	df.columns = ["ts"] + [q["q_id"] for q in survey["questions"]]		
	df['ts'] = pd.to_datetime(df['ts']).dt.strftime("%Y-%m-%d %H:%M")
	df.set_index('ts', inplace=True)			
	return ret.format(survey_id.upper(), repr(df))	

def survey(survey):
	ret = u"*===== _{}_ survey =====* \n".format(survey["id"].upper())
	qst = u"> *{}*: _{}_\n{}"		
	opt = u"`{}`   {}"		
	for i,q in enumerate(survey["questions"]):			
		choices = u"\n".join([opt.format(ascii_letters[e],c) for e,c in enumerate(q["choices"])])
		ret+= qst.format(q["q_id"], q["question"], choices)
		ret+=u"\n\n"
	ret += u"*====================*"
	return ret		

def survey_list( user_surveys, other_surveys):
	active=u">*{}*\t`{}`\t`{}`"
	inactive=u"~{}~"
	us = [active.format(s,r[0],r[1]) for s, r in user_surveys.items()]
	ot = [inactive.format(s) for s in other_surveys]
	display = u"*Your Surveys*\n{}\n{}"
	return display.format("\n".join(us),"\n".join(ot))

def attach_answer(a,survey_id, cancel_button=True, ok_button=False, notes_button=False):
	notes = None
	if "notes" in a: notes = a["notes"]			
	
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

	actions = []
	if cancel_button:
		actions.append({"name": "cancel",
			        	"text": "cancel",
			        	"type": "button",		        
			        	"value":"cancel", 
			        	"style":"danger"})
	if ok_button:
		actions.append({"name": "ok",
		        		"text": "ok",
		        		"type": "button",	
		        		"style": "primary",	        
		        		"value":"ok" })
	if notes_button:
		actions.append({"name": "notes",
		        		"text": "notes",
		        		"type": "button",		        
		        		"value":"notes" })

	attach = [{ "fallback": "reponse",
        		 "color": "good",		        		          		 
        		 "pretext": "These were you responses",
        		 u"title":"{} survey".format(survey_id.upper()),
        		 "callback_id":"answer",
        	     "fields":field_list,
        	     "text":" ",        	     
        	     "mrkdwn_in": ["text","pretext","title","fields"]
		 				}]

	if notes is not None:
		attach.append({ "fallback": "notes",
        		 		"color": "warning",	
        		 		"title": "notes",	        
        		 		"callback_id":"answer",          		 
        		 		"text": u"_{}_".format(notes),        	     		
        	     		"mrkdwn_in": ["text","pretext","title","fields"]        	     		
		 				})
	
	attach.append({ "fallback": "notes",
        		 	"color": "#CCCCCC",	        		 		
        		 	"callback_id":"answer",          		         		 		
        	     	"mrkdwn_in": ["text","pretext","title","fields"],
        	     	"actions":actions        	     		
		 			})
	
	return attach

def attach_report(survey, data, notes):	

	survey_id = survey["id"]
	ret = u"*report _{}_*\n\n```{}```"
	#survey answer tables have the columns: id, user_id, timestamp, answer_1, ... , answer_N, notes
	#keeping only: ts, timestamp, answer_1, ... , answer_N
	df_answers = pd.DataFrame(data).iloc[:,2:-1]		
	df_answers.columns = ["ts"] + [q["q_id"] for q in survey["questions"]]		
	df_answers['ts'] = pd.to_datetime(df_answers['ts']).dt.strftime("%Y-%m-%d %H:%M")
	# set_trace()
	for q in survey["questions"]:
		q_id = q["q_id"]
		choices = q["choices"]
		answers = df_answers[q_id]
		df_answers[q_id] = map(lambda x: choices[int(x)], answers)

	df_answers.set_index('ts', inplace=True)			
	report = "```{}```".format(repr(df_answers))
	attach = [
    			{ "fallback": "Survey Report",
        		  "color": "good",
        		  "pretext": u"Here is your report for survey _{}_".format(survey_id),            
        		  "title": "Responses",            
        	      "text": report,
        	      "mrkdwn_in": ["text","pretext","title"] },
    	        
			]
	if len(notes) > 0:
		df_notes = pd.DataFrame(notes)
		df_notes.columns = ["ts","notes"]
		df_notes['ts'] = pd.to_datetime(df_notes['ts']).dt.strftime("%Y-%m-%d %H:%M")
		df_notes.set_index('ts', inplace=True)			
		notez = "```{}```".format(repr(df_notes))
		note_attach = { "fallback": "Survey Notes",
		        		  "color": "warning",		        		  
		        		  "title": "Notes",            
		        	      "text": notez,      
		        	      "mrkdwn_in": ["text","pretext","title"]
		 				}
		attach.append(note_attach)
	
	return attach

# def attach_report(survey, data, notes):

# 	survey_id = survey["id"]
# 	ret = u"*report _{}_*\n\n```{}```"

# 	#survey answer tables have the columns: id, user_id, timestamp, answer_1, ... , answer_N, notes
# 	#keeping only: ts, timestamp, answer_1, ... , answer_N
# 	df_answers = pd.DataFrame(data).iloc[:,2:-1]		
# 	df_answers.columns = ["ts"] + [q["q_id"] for q in survey["questions"]]		
# 	df_answers['ts'] = pd.to_datetime(df_answers['ts']).dt.strftime("%Y-%m-%d %H:%M")
# 	df_answers.set_index('ts', inplace=True)			
# 	report = "```{}```".format(repr(df_answers))
# 	attach = [
#     			{ "fallback": "Survey Report",
#         		  "color": "good",
#         		  "pretext": u"Here is your report for survey _{}_".format(survey_id),            
#         		  "title": "Responses",            
#         	      "text": report,
#         	      "mrkdwn_in": ["text","pretext","title"] },
    	        
# 			]
# 	if len(notes) > 0:
# 		df_notes = pd.DataFrame(notes)
# 		df_notes.columns = ["ts","notes"]
# 		df_notes['ts'] = pd.to_datetime(df_notes['ts']).dt.strftime("%Y-%m-%d %H:%M")
# 		df_notes.set_index('ts', inplace=True)			
# 		notez = "```{}```".format(repr(df_notes))
# 		note_attach = { "fallback": "Survey Notes",
# 		        		  "color": "warning",		        		  
# 		        		  "title": "Notes",            
# 		        	      "text": notez,      
# 		        	      "mrkdwn_in": ["text","pretext","title"]
# 		 				}
# 		attach.append(note_attach)
	
# 	return attach

def attach_survey(survey):
	attaches = []	

	for q_num, q in enumerate(survey["questions"]):			
		question = [{                    
                    "value": u"*{}*: _{}_".format(q["q_id"], q["question"]),
                    "short": False
                }]		
		actions = []
		for e,c in enumerate(q["choices"]):
			actions.append({
		                    "name": q_num,
		                    "text": u"{}".format(c),
		                    "type": "button",
		                    "value":e
			                })			

		x = { "fallback": "Survey",
    		   "color": "good",    		   
    	        "fields": question,
           		"callback_id": survey["id"],
	            "actions": actions,
    	       "mrkdwn_in": ["text","pretext","title","fields","buttons","actions"] 
    	      }
		attaches.append(x)		
	return attaches
	

def attach_survey_list( user_surveys, other_surveys):	
	active_list = []
	attach = []	
	if len(user_surveys) > 0:
		active_list.append({                    
	                    "value": "*Survey*",
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
	        		 "color": "good",  
	        		 "title": "Subscribed Surveys",
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
    		 		"color": "warning",
    		 		"title": "Available Surveys",
    	     		"fields":inactive_list,
    	     		"mrkdwn_in": ["text","pretext","title","fields"]})
   	return attach
	



