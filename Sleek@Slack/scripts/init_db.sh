if [[ -z "$1" ]]; then
	echo "ERROR: configuration file missing"
else	
	if [ ! -f $1 ]; then
    	echo "ERROR:" $1 "not found!"
	
	else
		CONFIG=$1	
		echo "READ CONF FROM " $CONFIG 
		echo "INITING BACKEND"
		python app.py -cfg $CONFIG -init -surveys DATA/surveys/
	fi
fi

