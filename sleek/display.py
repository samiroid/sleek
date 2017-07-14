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

def attach_report(survey, data, notes):

	survey_id = survey["id"]
	ret = u"*report _{}_*\n\n```{}```"

	#survey answer tables have the columns: id, user_id, timestamp, answer_1, ... , answer_N, notes
	#keeping only: ts, timestamp, answer_1, ... , answer_N
	df_answers = pd.DataFrame(data).iloc[:,2:-1]		
	df_answers.columns = ["ts"] + [q["q_id"] for q in survey["questions"]]		
	df_answers['ts'] = pd.to_datetime(df_answers['ts']).dt.strftime("%Y-%m-%d %H:%M")
	df_answers.set_index('ts', inplace=True)			
	report = "```{}```".format(repr(df_answers))
	attach = [
    			{ "fallback": "Survey Report",
        		  "color": "good",
        		  "pretext": "Here is your report for survey _{}_".format(survey_id),            
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

def attach_answer(a):
	notes = None
	if "notes" in a: notes = a["notes"]			
	
	field_list = []
	for f,v in a.items():
		if f=="notes":continue		
		field_list.append({                    
                    "value": "*{}*".format(f),
                    "short": True
                })
		field_list.append({                    
                    "value": "_{}_".format(str(v).replace(">","+")),
                    "short": True
                })

	attach = [{ "fallback": "Response",
        		 "color": "warning",		        		          		 
        		 "text": "your answers were",
        	     "fields":field_list,
        	     "mrkdwn_in": ["text","pretext","title","fields"]
		 				}]

	if notes is not None:
		attach.append({ "fallback": "Response",
        		 		"color": "good",	
        		 		"title": "notes",	        		          		 
        		 		"text": "_{}_".format(notes),        	     		
        	     		"mrkdwn_in": ["text","pretext","title","fields"]
		 				})
	pprint.pprint(attach)
	return attach
	# set_trace()
	# if notes is not None:
	# 	ret = u"Your answers\n>>>{}\n_notes_:```{}```".format(ans,notes)
	# else:
	# 	ret = u"Your answers\n>>>{}".format(ans)
	# return ret

def notes( survey_id, notes):
	ret = u"*notes _{}_*\n\n```{}```"		
	df = pd.DataFrame(notes)
	df.columns = ["ts","notes"]
	df['ts'] = pd.to_datetime(df['ts']).dt.strftime("%Y-%m-%d %H:%M")
	df.set_index('ts', inplace=True)			
	return ret.format(survey_id.upper(), repr(df))	

def survey_list( user_surveys, other_surveys):
	active=u">*{}*\t`{}`\t`{}`"
	inactive=u"~{}~"
	us = [active.format(s,r[0],r[1]) for s, r in user_surveys.items()]
	ot = [inactive.format(s) for s in other_surveys]
	display = u"*Your Surveys*\n{}\n{}"
	return display.format("\n".join(us),"\n".join(ot))



