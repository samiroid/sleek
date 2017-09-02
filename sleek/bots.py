from random import randint

class ChatBot(object): 
	
	__default_cfg={
				"announce": u"Hello I am a chatbot but I can't do much yet...",
				"ack": [u"ok",u"got it!",u"sure",u"no problem"],
				"greet": [u"hi",u"yo",u"hello",u"hey"],
				"help": u"We all need a little help sometimes :)",	
				"nack": [u"sorry, I didn't get that", 
						 u"I don't understand that command",
						 u"!?"],
				"oops": [u"oops", u"oh oh", u"ergh"]
				}

	
	def __init__(self, cfg=None):		

		self.__greets = None
		self.__acks = None
		self.__nacks = None
		self.__help = None
		self.__announce = None
		self.__oops = None

		if cfg is None:			
			self.__load_cfg(ChatBot.__default_cfg)
		else:			
			self.__load_cfg(cfg)

	def __load_cfg(self, cfg):
		"""
			Load ChatBot configuration. Any 
			cfg: dictionary with the following fields: greetings, acks, nacks, help
		"""

		# values not present in the config dictionary will be replaced with default values 
		try:
			self.__greets = cfg["greet"]
		except KeyError:
			self.__greets = ChatBot.__default_cfg["greet"]

		try:
			self.__acks = cfg["ack"]
		except KeyError:
			self.__acks = ChatBot.__default_cfg["ack"]
		
		try:
			self.__nacks = cfg["nack"]
		except KeyError:
			self.__nacks = ChatBot.__default_cfg["nack"]

		try:
			self.__help = cfg["help"]
		except KeyError:
			self.__help = ChatBot.__default_cfg["help"]

		try:
			self.__announce = cfg["announce"]
		except KeyError:
			self.__announce = ChatBot.__default_cfg["announce"]

		try:
			self.__oops = cfg["oops"]
		except KeyError:
			self.__oops = ChatBot.__default_cfg["oops"]

	def __get_rand(self, obj):
		"""
			return a random element from a list
		"""		
		r = randint(0, len(obj)-1)
		return obj[r]		

	def ack(self):
		return self.__get_rand(self.__acks)

	def announce(self, name):
		return self.__announce.format(name)

	def greet(self):
		return self.__get_rand(self.__greets)

	def help(self):
		return self.__help

	def nack(self):
		return self.__get_rand(self.__nacks)

	def oops(self):
		return self.__get_rand(self.__oops)

	def chat(self, tokens, context):				
		if tokens[0] in self.__greets:		
			return [self.greet()]
		elif "help" in tokens:
			return [self.help()]
		else:
			return [self.nack()]
			
