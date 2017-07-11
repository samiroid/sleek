CONFIG=DATA/confs/beta.cfg

INIT=1
if (($INIT == 1 )); then
	echo "INITING BACKEND"
	python sleek@slack.py -cfg $CONFIG -init -surveys DATA/surveys/
fi
python sleek@slack.py -cfg $CONFIG -connect -dbg