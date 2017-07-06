#load surveys
BACKEND=DATA/text_client.db
API_TOKEN=$SLACK_BOT_TOKEN
BOT_ID=U5T7Z7ZPV


#run
# python code/main.py -db $BACKEND -connect $API_TOKEN $BOT_ID

INIT=0
if (($INIT == 1 )); then
	echo "INITING BACKEND"
	python code/main.py -db $BACKEND -init -load_surveys DATA/surveys/
fi
python code/main.py -db $BACKEND -connect $API_TOKEN $BOT_ID -dbg #-verbose