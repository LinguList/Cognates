from collections import OrderedDict
import re

import constants



class Reader:
	### Initialization ###
	# Initializes the reader by setting the target filename and various data
	# structures that will be used for reading various input files.
	def __init__(self):
		# Meanings and their indices (1 - 200).
		self.meanings = OrderedDict()
		
		# Languages and their indices (1 - 95).
		self.languages = {}
		
		# For each meaning, the wordform for each language.
		self.wordforms = {}
		
		# POS tags of each of the 200 meanings.
		self.POSTags = OrderedDict()
		
		# Sound (letter) classes for each character (Dolgopolsky, 1986).
		self.soundClasses = {}
		
		# A dictionary of consonants.
		self.consonants = {}
		
		# For each meaning, for each CCN, all other CCNs it is doubtfully
		# cognate with. This is used later when pairing cognates into positive
		# and negative examples to ensure that forms which are doubtfully
		# cognate are not used as examples of non-cognates.
		self.dCognateCCNs = {}
		
		# cognateCCNs is a dictionary whose keys are meaning indices. Each
		# meaning has an associated dictionary of cognate groups (CCNs). Each
		# cognate dictionary contains various CCNs and associated cognate
		# dictionaries. Each cognate dictionary is structured has language
		# indices as keys and language word forms for each given meaning as
		# values. Due to issues in the data, the input data is cleaned by
		# removing entries that are ambiguous or are have CCNs that indicate
		# inconclusive cognateness decisions.
		self.cognateCCNs = {}
		
		# For each meaning, for each cognate group, all wordforms that are
		# cognates of each other.
		self.cognateSets = {}
		
		# Meaning and language indices, CCN and cognate group that are currently
		# being processed.
		self.currentMeaningIndex = 0
		self.currentLanguageIndex = 0
		self.currentCCN = 0
		self.lastCCN = 0
		self.lastCognateGroup = -1


	### Reading ###
	# Reads the various input data files.
	def read(self):
		self.readData()
		self.readPOSTags()
		self.readSoundClasses()
		self.readConsonants()
	
	
	# Reads the cognate dataset line by line, parses each line and populates the
	# associated data structures accordingly.
	def readData(self):
		with open(constants.IN, "rb") as data:
			for line in data:
				# Header line, indicates the beginning of a block.
				if line[0] == constants.HEADER:
					# Checks if the required amount of meanings has already been
					# processed.
					if self.currentMeaningIndex + 1 > constants.MEANING_COUNT:
						break
					self.processHeader(line)
				
				# Subheader line, indicates the beginning of a subblock.
				elif line[0] == constants.SUBHEADER:
					self.processSubheader(line)
				
				# Relationship line, describes relationships between two
				# subblocks.
				elif line[0] == constants.RELATIONSHIP:
					self.processRelationship(line)
				
				# Form line.
				else:
					# CCN0, CCN3 and CCN5 forms are ignored.
					if self.currentCCN == constants.CCN0:
						continue
					elif (self.currentCCN >= constants.CCN3_START) and (self.currentCCN <= constants.CCN3_END):
						continue
					elif (self.currentCCN >= constants.CCN5_START) and (self.currentCCN <= constants.CCN5_END):
						continue
					else:
						self.processForm(line)
	
		# Orders languages by their indices for better readability.
		self.languages = OrderedDict(sorted(self.languages.items(), key = lambda x: x[0]))
	
	
	# Reads in the POS tags.
	def readPOSTags(self):
		with open(constants.POS, "rb") as data:
			for i, line in enumerate(data):
				self.POSTags[i + 1] = line.strip()
	
	
	# Reads in character sound classes.
	def readSoundClasses(self):
		with open(constants.DOLGO, "rb") as data:
			for line in data:
				parts = line.split(":")
				chars = parts[1].split(",")
				
				for char in chars:
					self.soundClasses[char.strip("\n")] = parts[0]
	
	
	# Reads in the list of consonants.
	def readConsonants(self):
		with open(constants.CONS, "rb") as data:
			for line in data:
				for char in line.split(","):
					self.consonants[char.strip()] = char.strip()


	### Processing Lines ###
	# Processes the header line.
	def processHeader(self, line):
		meaningIndex = int(line[2 : 5])
		meaning = line[6 :].strip().lower()

		self.meanings[meaningIndex] = meaning
		self.cognateCCNs[meaningIndex] = {}
		
		self.currentMeaningIndex = meaningIndex


	# Processes the subheader line.
	def processSubheader(self, line):
		self.currentCCN = int(line.split()[1])
	
	
	# Processes the relationship line.
	def processRelationship(self, line):
		splitLine = line.split()
		
		firstCCN = int(splitLine[1])
		type = int(splitLine[2])
		secondCCN = int(splitLine[3])
		
		if type == constants.DOUBTFUL_COGNATION:
			self.addDoubtfulCCNs(firstCCN, secondCCN)
			self.addDoubtfulCCNs(secondCCN, firstCCN)


	# Processes the form line.
	def processForm(self, line):
		self.currentLanguageIndex = int(line[6 : 8])
		language = line[9 : 24].strip().lower().title()
		
		# Allows only a subset of all languages to be read.
		if self.currentLanguageIndex <= constants.LANGUAGE_COUNT:
			form = self.parseForms(line)
		
			# Adds the form to the cognateCCNs dictionary. Also adds the form to
			# its appropriate cognate group based on its CCN.
			if form:
				if self.currentCCN not in self.cognateCCNs[self.currentMeaningIndex]:
					self.cognateCCNs[self.currentMeaningIndex][self.currentCCN] = {}
				self.cognateCCNs[self.currentMeaningIndex][self.currentCCN][self.currentLanguageIndex] = form
	
				if self.currentMeaningIndex not in self.wordforms:
					self.wordforms[self.currentMeaningIndex] = {}
				self.wordforms[self.currentMeaningIndex][self.currentLanguageIndex] = form
	
				self.addToCognateGroup(form)
	
			# If an unseen language is encountered, it is added to the language
			# dictionary.
			if self.currentLanguageIndex not in self.languages:
				self.languages[self.currentLanguageIndex] = language
	
	
	# Parses a given form line to extract all wordforms.
	def parseForms(self, line):
		forms = []
		
		# While most multiple forms are provided using a comma-delimited list,
		# some are also delimited with a /.
		for form in re.split("/|,", line[25 :]):
			# Changes all kinds of weird spaces into a normal space.
			form = " ".join(form.split())
			
			# Lowercases the form.
			form = form.strip().lower()
			
			# Drops words that beging with - (these are not words but rather
			# indications of an alternative word ending).
			if form and form[0] == "-":
				form = ""
			
			# Drops parentheses (and everything inside them).
			form = re.sub(r"\([^)]*\)", "", form).strip()
			
			# Removes non-alphabetic characters (but leaves spaces).
			form = re.sub(r"([^\s\w]|_)+", "", form).strip()

			# If after all that stripping and splitting the form is still there,
			# it is added to the final form list.
			if len(form) > 0:
				forms.append(form)
	
		# If there is more than one form, it becomes impossible to distinguish
		# between cognates and non-cognates for the particular language and
		# meaning. Thus, all entries with multiple forms are ignored.
		return forms[0] if len(forms) == 1 else None
	
	
	### Parsing CCNs ###
	# Adds a pair of CCNs to the doubtful CCN dictionary.
	def addDoubtfulCCNs(self, firstCCN, secondCCN):
		if self.currentMeaningIndex not in self.dCognateCCNs:
			self.dCognateCCNs[self.currentMeaningIndex] = {}
		
		if firstCCN not in self.dCognateCCNs[self.currentMeaningIndex]:
			self.dCognateCCNs[self.currentMeaningIndex][firstCCN] = []
		
		if secondCCN not in self.dCognateCCNs[self.currentMeaningIndex][firstCCN]:
			self.dCognateCCNs[self.currentMeaningIndex][firstCCN].append(secondCCN)


	### Grouping ###
	# Selects the approapriate cognate group to add the current wordform to.
	def addToCognateGroup(self, form):
		if self.currentMeaningIndex not in self.cognateSets:
			self.lastCCN = 0
			self.lastCognateGroup = -1
			
			self.cognateSets[self.currentMeaningIndex] = {}
		
		# Each word in CCN1 gets its own cognate group.
		if self.currentCCN == constants.CCN1:
			self.lastCognateGroup += 1
			self.cognateSets[self.currentMeaningIndex][self.lastCognateGroup] = [(form, self.currentLanguageIndex)]

		# Each word in the same CCN2 goes to the same cognate group.
		# Each word in the same CCN4 goes to the same cognate group.
		else:
			if self.currentCCN == self.lastCCN:
				self.cognateSets[self.currentMeaningIndex][self.lastCognateGroup].append((form, self.currentLanguageIndex))
			else:
				self.lastCognateGroup += 1
				self.cognateSets[self.currentMeaningIndex][self.lastCognateGroup] = [(form, self.currentLanguageIndex)]

		self.lastCCN = self.currentCCN