#load surveys
BACKEND=DATA/sleek4slack.db
API_TOKEN=$SLEEK_4_SLACK_TOKEN
BOT_ID=U62QPNT8D

#get bot id
#python code/main.py -get_bot_id $SLEEK_4_SLACK_TOKEN "sleek"

#init backend
python code/main.py -db $BACKEND -init -load_surveys DATA/surveys/
#run
python code/main.py -db $BACKEND -connect $API_TOKEN $BOT_ID -dbg