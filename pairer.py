from __future__ import division

import constants



# There are 19,000 entries in the data. Out of those:
# 364 do not have forms associated with meanings (CCN0),
# 1,476 are unique (not cognate to any other forms in the data) (CCN1),
# 9,167 are cognate with each other (within their respective groups), but not
# with any other forms in the data (CCN2),
# 167 are doubtfully cognate with each other (within their respective groups),
# but not cognate with any other forms in the data (CCN3),
# 7,751 are cognate with each other (within their respective groups) and cognate
# or doubtfully cognate with at least one form from some other list (CCN4), and
# 75 are doubtfully cognate with each other (within their respective groups) and
# doubtfully cognate with at least one form from some other list (CCN5).

# For each meaning:
	# Positive examples:
		# CCN2: within single group.
		# CCN4: within single group.
	# Negative examples:
		# CCN1: within single group.
		# CCN1: with all forms from any CCN2 group.
		# CCN1: with all forms from any CCN3 group.
		# CCN1: with all forms from any CCN4 group.
		# CCN1: with all forms from any CCN5 group.

		# CCN2: with all forms from any other CCN2 group.
		# CCN2: with all forms from any CCN3 group.
		# CCN2: with all forms from any CCN4 group.
		# CCN2: with all forms from any CCN5 group.

		# CCN3: with all forms from any other CCN3 group.
		# CCN3: with all forms from any CCN4 group.
		# CCN3: with all forms from any CCN5 group.

		# CCN4: with all forms from any other CCN4 group (s.t. relationships).
		# CCN4: with all forms from any CCN5 group (s.t. relationships).

		# CCN5: with all forms from any other CCN5 group (s.t. relationships).

class Pairer:
	### Initialization ###
	# Initializes the pairer, sets the example and label dictionaries.
	def __init__(self):
		# Used internally.
		self.pExamples = {}
		self.pLabels = {}
		self.nExamples = {}
		self.nLabels = {}
		
		# Used for later access in the main script. The three dictionary entries
		# correspond to the training and test example lists.
		self.examples = {x: [] for x in range(3)}
		self.labels = {x: [] for x in range(3)}
		
		self.allCounts = {x: 0 for x in range(4)}
		self.positiveCounts = {x: 0 for x in range(4)}
		
		self.testMeanings = []
		self.testLanguages = []
		
		self.meaningRange = {
			constants.TRAIN: {key: 0 for key in range(constants.MEANING_COUNT + 1)},
			constants.TEST: {key: 0 for key in range(constants.MEANING_COUNT + 1)}
		}
	

	### Pairing ###
	# The data is divided into training and test sets by meaning. A fraction
	# (tRatio) of the meanings is used as training data, the rest of the data is
	# used for testing.
	def pairByMeaningRatio(self, cognates, dCognates, tRatio):
		self.pair(cognates, dCognates)
		self.combinePairs(tRatio)
		
		self.testLanguages = range(1, constants.LANGUAGE_COUNT + 1)
		self.testMeanings = range(int(constants.MEANING_COUNT * tRatio) + 1, constants.MEANING_COUNT + 1)
	
	
	# The data is divided into training and test sets by languages. tRatio
	# decides the fraction of all languages to be used as training data. The
	# rest of the data is used for testing purposes.
	def pairByLanguageRatio(self, cognates, dCognates, tRatio):
		countTrain = int(constants.LANGUAGE_COUNT * tRatio)
		trainLanguages = range(1, countTrain + 1)
		self.pairByLanguage(cognates, dCognates, trainLanguages)
	
		self.testLanguages = range(countTrain + 1, constants.LANGUAGE_COUNT + 1)
		self.testMeanings = range(1, constants.MEANING_COUNT + 1)
	
	
	# The data is assigned to the training set only for languages specified in
	# the trainLanguages list. The remaining data is used for testing.
	def pairBySpecificLanguage(self, cognates, dCognates, trainLanguages):
		self.pairByLanguage(cognates, dCognates, trainLanguages)
	
		self.testLanguages = [i for i in range(1, constants.LANGUAGE_COUNT + 1) if i not in trainLanguages]
		self.testMeanings = range(1, constants.MEANING_COUNT + 1)
	
	
	# Splits the data into training and testing sets by language.
	def pairByLanguage(self, cognates, dCognates, trainLanguages):
		trainCognates = {}
		testCognates = {}
		
		for meaningIndex, CCNs in cognates.iteritems():
			trainCognates[meaningIndex] = {}
			testCognates[meaningIndex] = {}
			
			for CCN, forms in CCNs.iteritems():
				trainCognates[meaningIndex][CCN] = {}
				testCognates[meaningIndex][CCN] = {}
				
				for languageIndex, form in forms.iteritems():
					if languageIndex in trainLanguages:
						trainCognates[meaningIndex][CCN][languageIndex] = form
					else:
						testCognates[meaningIndex][CCN][languageIndex] = form

		self.pair(trainCognates, dCognates)
		self.combineTrainingPairs()
		
		self.pair(testCognates, dCognates)
		self.combineTestPairs()
	
	
	# Pairs wordforms as either positive or negative examples using rules based
	# on CCN group numbers and cognate group relationships.
	def pair(self, cognates, dCognates):
		for meaningIndex, CCNs in cognates.iteritems():
			self.pExamples[meaningIndex] = []
			self.pLabels[meaningIndex] = []
			self.nExamples[meaningIndex] = []
			self.nLabels[meaningIndex] = []
			
			self.pairCCNs(meaningIndex, CCNs, dCognates)


	# Combines positive and negative examples, and divides them into training
	# and testing sets based on provided ratios.
	def combinePairs(self, tRatio):
		meaningCount = len(self.pExamples)
		countTrain = int(meaningCount * tRatio)
		
		for i in range(1, meaningCount + 1):
			if i <= countTrain:
				self.extendDataset(constants.TRAIN, i)
			else:
				self.extendDataset(constants.TEST, i)


	# Combines positive and negative examples only for the training data.
	def combineTrainingPairs(self):
		meaningCount = len(self.pExamples)
	
		for i in range(1, meaningCount + 1):
			self.extendDataset(constants.TRAIN, i)


	# Combines positive and negative examples only for the test data.
	def combineTestPairs(self):
		meaningCount = len(self.pExamples)
		
		for i in range(1, meaningCount + 1):
			self.extendDataset(constants.TEST, i)


	# Extends the dataset.
	def extendDataset(self, purpose, i):
		self.examples[purpose].extend(self.pExamples[i])
		self.examples[purpose].extend(self.nExamples[i])
		
		self.labels[purpose].extend(self.pLabels[i])
		self.labels[purpose].extend(self.nLabels[i])
		
		self.allCounts[purpose] += len(self.pExamples[i]) + len(self.nExamples[i])
		self.positiveCounts[purpose] += len(self.pExamples[i])
		
		self.allCounts[constants.ALL] += len(self.pExamples[i]) + len(self.nExamples[i])
		self.positiveCounts [constants.ALL] += len(self.pExamples[i])
		
		self.meaningRange[purpose][i] = len(self.labels[purpose])


	# Pairs each wordform with a number of other wordforms to generate either a
	# positive or negative example. CCN1, CCN3, CCN4 and CCN5 only controbute to
	# the negative examples. Items from the same cognate group in CCN2 and CCN4
	# contribute to positive examples.
	def pairCCNs(self, meaningIndex, CCNs, dCognates):
		for CCN, forms in CCNs.iteritems():
			for i in range(0, len(forms)):
				if CCN == constants.CCN1:
					# CCN1: negative examples within single group.
					examples, labels = self.matchWithinGroup(i, forms, 0)
					
					self.nExamples[meaningIndex].extend(examples)
					self.nLabels[meaningIndex].extend(labels)
				
				elif (CCN >= constants.CCN2_START and CCN <= constants.CCN2_END) or (CCN >= constants.CCN4_START and CCN <= constants.CCN4_END):
					# CCN2: positive examples withing single group.
					# CCN4: positive examples withing single group.
					examples, labels = self.matchWithinGroup(i, forms, 1)
					
					self.pExamples[meaningIndex].extend(examples)
					self.pLabels[meaningIndex].extend(labels)
				
				for otherCCN, otherForms in CCNs.iteritems():
					if (otherCCN > CCN) and (meaningIndex not in dCognates or self.notDoubtful(CCN, otherCCN, dCognates[meaningIndex])):
						self.pairWithOtherNegatives(meaningIndex, i, forms, otherForms)
				


	# Pairs a single wordform with all other wordforms that constitute a
	# negative example.
	def pairWithOtherNegatives(self, meaningIndex, i, forms, otherForms):
		languageIndices = forms.keys()
		currentForm = forms[languageIndices[i]]
		examples, labels = self.matchWithOtherGroup(currentForm, languageIndices[i], otherForms, 0)
		
		self.nExamples[meaningIndex].extend(examples)
		self.nLabels[meaningIndex].extend(labels)


	# Pairs the given wordform with all other wordforms that come later in the
	# wordform dictionary.
	def matchWithinGroup(self, i, forms, label):
		languageIndices = forms.keys()
	
		examples = []
		labels = []
	
		for j in range(i + 1, len(languageIndices)):
			# Example is a tuple of two word forms and two language IDs.
			example = (forms[languageIndices[i]], forms[languageIndices[j]], languageIndices[i], languageIndices[j])
			examples.append(example)
			labels.append(label)
	
		return examples, labels
	

	# Pairs the given wordform with all other wordforms in another wordform
	# dictionary.
	def matchWithOtherGroup(self, form, languageIndex, otherForms, label):
		examples = []
		labels = []
	
		for otherLanguageIndex, otherForm in otherForms.iteritems():
			example = (form, otherForm, languageIndex, otherLanguageIndex)
			examples.append(example)
			labels.append(label)
	
		return examples, labels


	# Checks if the two CCNs are not in a doubtful cognation relationship.
	def notDoubtful(self, CCN1, CCN2, dCognates):
		if (CCN1 in dCognates) and (CCN2 in dCognates[CCN1]):
			return False
		else:
			return True