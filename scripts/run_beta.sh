CONFIG=DATA/confs/beta.cfg
API_TOKEN_ID="SLEEK_BETA_TOKEN"
INIT=1
if (($INIT == 1 )); then
	echo "INITING BACKEND"
	python sleek@slack.py -cfg $CONFIG -init -surveys DATA/surveys/
else
	python sleek@slack.py -cfg $CONFIG -connect $API_TOKEN_ID -dbg
fi
