#load surveys
API_TOKEN=$SLEEK_BETA_TOKEN
BOT_NAME=sleek
CONFIG=DATA/confs/beta.cfg

INIT=0
if (($INIT == 1 )); then
	echo "INITING BACKEND"
	python code/run_dev.py -cfg $CONFIG -init -load_surveys DATA/surveys/
fi
python code/run_dev.py -cfg $CONFIG -connect $API_TOKEN $BOT_NAME -greet "#general" -dbg




