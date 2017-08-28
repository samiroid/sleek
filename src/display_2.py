import pandas as pd
from string import ascii_letters
from ipdb import set_trace
import pprint

# methods to format the replies
def answer(a, notes=None):		
	ans = u"\n".join(["*{}*: {}".format(f,v) for f,v in a.items() if f!="notes"])
	if notes is not None:
		ret = u"Your answers\n>>>{}\n_notes_:```{}```".format(ans,notes)
	else:
		ret = u"Your answers\n>>>{}".format(ans)
	return ret

def notes(survey_id, notes):
	ret = u"*notes _{}_*\n\n```{}```"		
	df = pd.DataFrame(notes)
	df.columns = ["ts","notes"]
	df['ts'] = pd.to_datetime(df['ts']).dt.strftime("%Y-%m-%d %H:%M")
	df.set_index('ts', inplace=True)			
	return ret.format(survey_id.upper(), repr(df))	

def report(survey, data):
	survey_id = survey["id"]
	ret = u"*report _{}_*\n\n```{}```"	
	#survey answer tables have the columns: id, user_id, timestamp, answer_1, ... , answer_N, notes
	#keeping only: ts, answer_1, ... , answer_N
	df_answers = pd.DataFrame(data).iloc[:,2:-1]		
	df_answers.columns = ["ts"] + [q["q_id"] for q in survey["questions"]]		
	df_answers['ts'] = pd.to_datetime(df_answers['ts']).dt.strftime("%Y-%m-%d %H:%M")
	#convert numeric answers back to their text values
	for q in survey["questions"]:
		q_id = q["q_id"]
		choices = q["choices"]
		answers = df_answers[q_id]
		df_answers[q_id] = map(lambda x: choices[int(x)], answers)
	df_answers.set_index('ts', inplace=True)	
	return ret.format(survey_id.upper(), repr(df_answers))	

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




