#load surveys
BACKEND=DATA/text_client.db
API_TOKEN=$SLACK_BOT_TOKEN
BOT_ID=U5T7Z7ZPV
#python code/main.py -db $BACKEND -init -load_surveys DATA/surveys/

#run
# python code/main.py -db $BACKEND -connect $API_TOKEN $BOT_ID
python code/main.py -db $BACKEND -connect $API_TOKEN $BOT_ID -dbg