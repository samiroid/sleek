import pandas as pd
from string import ascii_letters
   
   
# methods to format the replies
def answer(a):
	notes = None
	if "notes" in a: notes = a["notes"]			
	ans = u"\n".join(["*{}*: {}".format(f,v) for f,v in a.items() if f!="notes"])
	if notes is not None:
		out = u"Your answers\n>>>{}\n_notes_:```{}```".format(ans,notes)
	else:
		out = u"Your answers\n>>>{}".format(ans)
	return out
	
def survey(survey):
	out = u"*===== _{}_ survey =====* \n".format(survey["id"].upper())
	qst = u"> *{}*: _{}_\n{}"		
	opt = u"`{}`   {}"		
	for i,q in enumerate(survey["questions"]):			
		choices = u"\n".join([opt.format(ascii_letters[e],c) for e,c in enumerate(q["choices"])])
		out+= qst.format(q["q_id"], q["question"], choices)
		out+=u"\n\n"
	out += u"*====================*"
	return out		

def report(survey, data):
	survey_id = survey["id"]
	out = u"*report _{}_*\n\n```{}```"
	#survey = current_surveys[survey_id]["questions"]
	#survey answer tables have the columns: id, user_id, timestamp, answer_1, ... , answer_N, notes
	#keeping only: ts, timestamp, answer_1, ... , answer_N
	df = pd.DataFrame(data).iloc[:,2:-1]		
	df.columns = ["ts"] + [q["q_id"] for q in survey["questions"]]		
	df['ts'] = pd.to_datetime(df['ts']).dt.strftime("%Y-%m-%d %H:%M")
	df.set_index('ts', inplace=True)			
	return out.format(survey_id.upper(), repr(df))	

def notes( survey_id, notes):
	out = u"*notes _{}_*\n\n```{}```"		
	df = pd.DataFrame(notes)
	df.columns = ["ts","notes"]
	df['ts'] = pd.to_datetime(df['ts']).dt.strftime("%Y-%m-%d %H:%M")
	df.set_index('ts', inplace=True)			
	return out.format(survey_id.upper(), repr(df))	

def survey_list( user_surveys, other_surveys):
	active=u">*{}*\t`{}`\t`{}`"
	inactive=u"~{}~"
	us = [active.format(s,r[0],r[1]) for s, r in user_surveys.items()]
	ot = [inactive.format(s) for s in other_surveys]
	display = u"*Your Surveys*\n{}\n{}"
	return display.format("\n".join(us),"\n".join(ot))