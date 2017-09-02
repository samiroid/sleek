from ipdb import set_trace
import sys
#sleek
sys.path.append("sleek")
import sleek 

def test_confs():
	
	cfg={ 
		  "greet": ["ciao","oi","holla :)"],
		  "announce": "This is a test chat bot",
		  "nack": ["q?!", "no lo se","!?"],
	      "ack": ["roger","okidoki"],
		  "help": "Please some help!"	
		}
	#create Sleek instance with default config
	bot = sleek.Sleek()
	assert bot.greet() in sleek.Sleek.default_cfg["greet"]
	assert bot.ack() in sleek.Sleek.default_cfg["ack"]
	assert bot.nack() in sleek.Sleek.default_cfg["nack"]
	assert bot.announce() == sleek.Sleek.default_cfg["announce"]
	assert bot.help() == sleek.Sleek.default_cfg["help"]

	#create sleek.Sleek instance with custom config
	bot2 = sleek.Sleek(cfg=cfg)
	assert bot2.greet() in cfg["greet"]
	assert bot2.ack() in cfg["ack"]
	assert bot2.nack() in cfg["nack"]
	assert bot2.help() in cfg["help"]
	assert bot2.announce() in cfg["announce"]
	

