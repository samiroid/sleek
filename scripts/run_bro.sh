CONFIG=DATA/confs/bro.cfg
API_TOKEN_ID="BRO_TOKEN"
INIT=0
if (($INIT == 1 )); then
	echo "INITING BACKEND"
	python sleek@slack.py -cfg $CONFIG -init -surveys DATA/surveys/
else
	python sleek@slack.py -cfg $CONFIG -api_token_id $API_TOKEN_ID -connect -dbg 
fi
