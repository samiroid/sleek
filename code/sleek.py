from ipdb import set_trace
from random import randint

class Sleek(object): 
	
	default_cfg={
				"announce": "Hello I am a Sleek chatbot but I can't do much yet...",
				"ack": ["ok","got it!","sure","no problem"],
				"greet": ["hi","yo","hello :)"],
				"help": "We all need a little help sometimes :)",	
				"nack": ["sorry, I didn't get that", "I don't understand that command","!?"]
				}

	
	def __init__(self, cfg=None):		

		self.__greets = None
		self.__acks = None
		self.__nacks = None
		self.__help = None
		self.__announce = None

		if cfg is None:			
			self.__load_cfg(Sleek.default_cfg)
		else:			
			self.__load_cfg(cfg)

	def __load_cfg(self, cfg):
		"""
			Load sleek configuration. Any 
			cfg: dictionary with the following fields: greetings, acks, nacks, help
		"""

		# values not present in the config dictionary will be replaced with default values 
		try:
			self.__greets = cfg["greet"]
		except KeyError:
			self.__greets = Sleek.default_cfg["greet"]

		try:
			self.__acks = cfg["ack"]
		except KeyError:
			self.__acks = Sleek.default_cfg["ack"]
		
		try:
			self.__nacks = cfg["nack"]
		except KeyError:
			self.__nacks = Sleek.default_cfg["nack"]

		try:
			self.__help = cfg["help"]
		except KeyError:
			self.__help = Sleek.default_cfg["help"]

		try:
			self.__announce = cfg["announce"]
		except KeyError:
			self.__announce = Sleek.default_cfg["announce"]

	def __get_rand(self, obj):
		"""
			return a random element from a list
		"""		
		r = randint(0, len(obj)-1)
		return obj[r]		

	def ack(self):
		return self.__get_rand(self.__acks)

	def announce(self):
		return self.__announce

	def greet(self):
		return self.__get_rand(self.__greets)

	def help(self):
		return self.__help

	def nack(self):
		return self.__get_rand(self.__nacks)

	def chat(self, tokens, context):		
		#TODO: this is kinda hacky :)
		# if len(set(self.__greets) & set(tokens.split())) > 0:		
		# 	return self.greet()
		if tokens[0] in self.__greets:		
			return self.greet()
		elif "help" in tokens:
			return self.help()
		else:
			return self.nack()	
	
