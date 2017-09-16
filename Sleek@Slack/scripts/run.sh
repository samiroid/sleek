if [[ -z "$1" ]]; then
	echo "ERROR: configuration file missing"
else	
	if [ ! -f $1 ]; then
    	echo "ERROR:" $1 "not found!"
	
	else
		CONFIG=$1	
		echo "read config @" $CONFIG 
		echo "** connecting **"
		#run
		python app.py -cfg $CONFIG -connect -dbg  
	fi
fi

