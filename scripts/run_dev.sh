#load surveys
API_TOKEN=$SLEEK_DEV_TOKEN
BOT_NAME=sleek
CONFIG=DATA/confs/dev.cfg

INIT=0
if (($INIT == 1 )); then
	echo "INITING BACKEND"
	python src/main.py -cfg $CONFIG -init -load_surveys DATA/surveys/
fi
python src/main.py -cfg $CONFIG -connect $API_TOKEN $BOT_NAME -greet "#general" -dbg




