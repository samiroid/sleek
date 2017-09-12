CONFIG=DATA/confs/beta.cfg
API_TOKEN_ID="SLEEK_BETA_TOKEN"

if [[ -z "$1" ]]; then
	INIT=0
else
	INIT=$1
	fi
if (($INIT == 1 )); then
	echo "INITING BACKEND"
	python main.py -cfg $CONFIG -init -surveys DATA/surveys/
fi
if (($INIT == 2 )); then
	echo "UPDATING BACKEND"
	python main.py -cfg $CONFIG -surveys DATA/surveys/
fi
echo "CONNECTING"
python main.py -cfg $CONFIG -api_token_id $API_TOKEN_ID -connect -dbg  
