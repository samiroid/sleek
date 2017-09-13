if [[ -z "$1" ]]; then
	echo "ERROR: configuration file missing"
else	
	if [ ! -f $1 ]; then
    	echo "ERROR:" $1 "not found!"
	
	else
		CONFIG=$1	
		echo "READ CONF FROM " $CONFIG 
		echo "CONNECTING"
		#run
		python main.py -cfg $CONFIG -connect -dbg  
	fi
fi

