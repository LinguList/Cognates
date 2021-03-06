from __future__ import division
from collections import OrderedDict
import math
import os

import Levenshtein
import numpy

import constants



class Extractor:
	### Initialization ###
	# Initializes training and test set data structures.
	def __init__(self):
		# Measures
		self.identicalWordsMeasure = [self.identicalWords]
		self.identicalFirstLetterMeasure = [self.identicalFirstLetter]
		self.identicalPrefixMeasure = [self.identicalPrefix]
		self.HK2011Measures = [self.basicMED, self.LCPLength, self.commonBigramNumber, self.longerWordLen, self.shorterWordLen, self.wordLenDifference]
		self.minimalMeasures = [self.LCPRatio, self.bigramDice]
		
		self.negativeMeasure = [self.sharedLetter]
		
		self.allMeasures = [self.identicalWords, self.identicalPrefix, self.identicalFirstLetter, self.basicMED, self.basicNED, self.jaroDistance, self.jaroWinklerDistance, self.LCPLength, self.LCPRatio, self.LCSLength, self.LCSR, self.bigramDice, self.commonBigramNumber, self.commonBigramRatio, self.trigramDice, self.commonTrigramNumber, self.commonTrigramRatio, self.xBigramDice, self.xxBigramDice, self.commonXBigramNumber, self.commonXBigramRatio, self.commonLetterNumber, self.commonLetterRatio, self.longerWordLen, self.shorterWordLen, self.averageWordLen, self.wordLenDifference, self.wordLenDifferenceRatio]
		
		self.trainExamples = []
		self.trainLabels = []
		self.testExamples = []
		self.testLabels = []
	
		self.consonantPrep = None
		self.soundClassPrep = None
	
	
	# Resets training and test features. Allows using the same object multiple
	# times with different feature extraction strategies.
	def cleanup(self):
		self.trainExamples = []
		self.trainLabels = []
		
		self.testExamples = []
		self.testLabels = []
	
	
	### Pairwise Methods ###
	# Identical words baseline (pairwise deduction).
	def identicalWordsBaseline(self, allExamples, allLabels):
		self.appendWordSimilarityFeatures(allExamples, allLabels, self.identicalWordsMeasure)
	
	
	# Identical prefix baseline (pairwise deduction).
	def identicalPrefixBaseline(self, allExamples, allLabels):
		self.appendWordSimilarityFeatures(allExamples, allLabels, self.identicalPrefixMeasure)
	
	
	# Identical first letter baseline (pairwise deduction).
	def identicalFirstLetterBaseline(self, allExamples, allLabels):
		self.appendWordSimilarityFeatures(allExamples, allLabels, self.identicalFirstLetterMeasure)
	
	
	# A reproduction of Hauer & Kondrak (2011). Since data has been preprocessed
	# slightly differently in this project, and in some cases Hauer & Kondrak
	# only provide minimal implementation information, a *true* comparison among
	# the different approaches can only be performed if the Hauer & Kondrak
	# approach is re-implemented.
	def HK2011Baseline(self, allExamples, allLabels):
		# Minimum edit distance (here used with all costs equal to 1)
		# Longest common prefix length
		# Number of common bigrams
		# Length of the first word (here length of the shorter word)
		# Length of the second word (here length of the longer word)
		# Absolute length difference between the two words
		self.appendWordSimilarityFeatures(allExamples, allLabels, self.HK2011Measures)


	### Group-based Methods ###
	# Arranges wordforms into groups of identical items.
	def identicalWordsGroupBaseline(self, testMeanings, testLanguages, wordforms):
		return self.groupBaseline(self.getWordform, testMeanings, testLanguages, wordforms)
	
	
	# Arranges wordforms into groups of items sharing the first 4 letters (note
	# that if a word is shorter than 4 letters, it is automatically placed in
	# a separate cluster).
	def identicalPrefixGroupBaseline(self, testMeanings, testLanguages, wordforms):
		return self.groupBaseline(self.getPrefix, testMeanings, testLanguages, wordforms)
	
	
	# Arranges wordforms into groups of items sharing the same first letter.
	def identicalFirstLetterGroupBaseline(self, testMeanings, testLanguages, wordforms):
		return self.groupBaseline(self.getFirstLetter, testMeanings, testLanguages, wordforms)
	
	
	# Arranges wordforms for each meaning in groups of cognates, where a
	# cognateness decision is made based on the test method provided. The test
	# dataset is used.
	def groupBaseline(self, test, testMeanings, testLanguages, wordforms):
		clusters = OrderedDict()
		
		for meaningIndex in testMeanings:
			lastClusterIndex = -1
			clusterIndices = {}
			clusters[meaningIndex] = {}
			
			for languageIndex, wordform in wordforms[meaningIndex].iteritems():
				key = test(wordform)
				
				# If the provided test returns None, the wordform is placed in
				# its own separate group.
				if key is None:
					lastClusterIndex += 1
					clusters[meaningIndex][lastClusterIndex] = [(wordform, languageIndex)]
				else:
					# clusterIndices stores keys provided by the test method and
					# their corresponding group numbers. This allows numbering
					# groups using consecutive numbers starting with zero.
					if key not in clusterIndices:
						lastClusterIndex += 1
						clusterIndices[key] = lastClusterIndex
				
					clusterIndex = clusterIndices[key]
					if clusterIndex not in clusters[meaningIndex]:
						clusters[meaningIndex][clusterIndex] = []
					clusters[meaningIndex][clusterIndex].append((wordform, languageIndex))
	
		labels = self.extractGroupLabels(clusters, wordforms, testMeanings, testLanguages)
		
		return labels, clusters
	
	
	### Extractors ###
	# Extracts a set of features (all used in Hauer & Kondrak) from a pair of
	# words.
	def HK2011Extractor(self, form1, form2, languages = None, language1 = None, language2 = None, meaningIndex = None, POSTags = None):
		example = [test(form1, form2) for test in self.HK2011Measures]
		return numpy.array(example)
	
	
	# Extracts a set of features (all used in Hauer & Kondrak) from a pair of
	# words. Includes language pair features,
	def HK2011ExtractorFull(self, form1, form2, languages, language1, language2, meaningIndex = None, POSTags = None):
		example = [test(form1, form2) for test in self.HK2011Measures]
		example.extend(self.exampleBinaryLanguageFeature(languages, language1, language2))
		return numpy.array(example)
	
	
	# Extracts minimal approach features: the longest common prefix ratio,
	# bigram Dice's coefficient, and 11 POS tags.
	def minimalExtractor(self, form1, form2, languages, language1, language2, meaningIndex, POSTags):
		# Extracts orthographic similarity features.
		example = [test(form1, form2) for test in self.minimalMeasures]
		
		# Extracts POS tag features.
		example.extend(self.examplePOSTagFeature(POSTags, meaningIndex))

		return numpy.array(example)
	
	
	# Extracts combined approach features: a number of word similarity measures
	# (some with additional string preprocessing), POS tags, letter
	# correspondences, and language grouping.
	def combinedExtractor(self, form1, form2, languages, language1, language2, meaningIndex, POSTags):
		# Extracts orthographic similarity features.
		example = [test(form1, form2) for test in [self.commonBigramRatio, self.commonTrigramNumber, self.bigramDice, self.jaroDistance]]
		example.extend([test(self.preprocess(form1, self.consonantPrep), self.preprocess(form2, self.consonantPrep)) for test in [self.identicalWords]])
		example.extend([test(self.preprocess(form1, self.soundClassPrep), self.preprocess(form2, self.soundClassPrep)) for test in [self.LCPLength, self.commonBigramNumber, self.identicalPrefix]])
		
		# Extracts POS tag features.
		example.extend(self.examplePOSTagFeature(POSTags, meaningIndex))
	
		# Extracts letter correspondence features.
		operations = self.exampleLetterFeature(form1, form2)
		indices = numpy.triu_indices_from(operations)
		example.extend(numpy.asarray(operations[indices]))
	
		# Extracts language group features.
		languageGroups = self.getLanguageGroups()
		example.append(self.exampleSameLanguageGroupFeature(languageGroups, language1, language2))
	
		return numpy.array(example)
	
	
	### POS Tags ###
	# Appends binary POS tag features to each examples. POS tags are decided
	# based on the English meaning rather than the particular language word.
	def appendPOSTags(self, allExamples, allLabels, POSTags):
		tags = sorted(list(set(POSTags.values())))
		
		for purpose, examples in allExamples.iteritems():
			tagFeatures = numpy.zeros((len(allExamples[purpose]), len(tags)))
			
			for i, (form1, form2, language1, language2, meaningIndex) in enumerate(examples):
				tagIndex = tags.index(POSTags[meaningIndex])
				tagFeatures[i, tagIndex] = 1.0
			
			self.stackExamples(purpose, tagFeatures)
			self.setLabels(purpose, numpy.array(allLabels[purpose]))


	# Given a single example, generates a set of binary POS tag features.
	def examplePOSTagFeature(self, POSTags, meaningIndex):
		tags = sorted(list(set(POSTags.values())))
		tagFeatures = [0.0] * len(tags)
		tagFeatures[tags.index(POSTags[meaningIndex])] = 1.0
	
		return tagFeatures

	
	### Language Similarity ###
	# Extracts the necessary language similarity values from the language
	# similarity matrix, appends the new feature to the existing test set.
	def appendTestLanguageSimilarities(self, predictedSimilarities, allExamples):
		similarityFeature = []
		
		for i, (form1, form2, language1, language2, meaningIndex) in enumerate(allExamples[constants.TEST]):
			similarityFeature.append(predictedSimilarities[language1][language2])
		
		self.testExamples = numpy.hstack((self.testExamples, numpy.array(similarityFeature)))
	
	
	# Measures language similarity as a fraction of positive examples to all
	# examples for each language pair in the training set.
	def appendTrainLanguageSimilarities(self, allExamples):
		decisionCounts = self.countTrainDecisions(allExamples)
		decisionSimilarities = self.computeTrainLanguageSimilarity(allExamples, decisionCounts)
		
		self.trainExamples = numpy.column_stack((self.trainExamples, numpy.array(decisionSimilarities)))
	
	
	# For each example, adds a set of binary language pair features. All
	# features are 0 except for a single feature that corresponds to the
	# example's language pair. That feature is set to 1. Used in Hauer &
	# Kondrak, 2011.
	def appendBinaryLanguageFeatures(self, allExamples, allLabels, purpose, languages):
		languageFeatures = [[] for i in range(len(allExamples[purpose]))]
		
		for i, (form1, form2, language1, language2, meaningIndex) in enumerate(allExamples[purpose]):
			languageFeatures[i] = self.exampleBinaryLanguageFeature(languages, language1, language2)
		
		self.stackExamples(purpose, numpy.array(languageFeatures))
		self.setLabels(purpose, numpy.array(allLabels[purpose]))
	
	
	# Adds s single binary feature to each example. 1 indicates that the two
	# words come from closely related languages.
	def appendSameLanguageGroupFeatures(self, allExamples, allLabels):
		languageGroups = self.getLanguageGroups()
		
		for purpose, examples in allExamples.iteritems():
			languageFeatures = []
			
			for i, (form1, form2, language1, language2, meaningIndex) in enumerate(examples):
				languageFeatures.append(self.exampleSameLanguageGroupFeature(languageGroups, language1, language2))
			
			self.stackExamples(purpose, numpy.array(languageFeatures))
			self.setLabels(purpose, numpy.array(allLabels[purpose]))
	

	# Given a single example, returns 1.0 if the two words in the example belong
	# to languages of the same language group.
	def exampleSameLanguageGroupFeature(self, languageGroups, language1, language2):
		return 1.0 if languageGroups[language1] == languageGroups[language2] else 0.0
	
	
	# Formats language group information.
	def getLanguageGroups(self):
		languageGroups = {}
		for i, languages in enumerate(constants.LANGUAGE_GROUPS):
			for language in languages:
				languageGroups[language] = i

		return languageGroups


	# Given a single example, generates a set of binary language pair features.
	def exampleBinaryLanguageFeature(self, languages, language1, language2):
		languageMatrix = numpy.zeros((len(languages), len(languages)))
		languageMatrix[language1 - 1][language2 - 1] = 1.0
		languageMatrix[language2 - 1][language1 - 1] = 1.0
		
		indices = numpy.triu_indices_from(languageMatrix, 1)
		return numpy.asarray(languageMatrix[indices])


	# Uses the training dataset to count positive and all cognateness decisions
	# for language pairs present in the data.
	def countTrainDecisions(self, allExamples):
		decisionCounts = {}
		
		for i, (form1, form2, language1, language2, meaningIndex) in enumerate(allExamples[constants.TRAIN]):
			if language1 not in decisionCounts:
				decisionCounts[language1] = {}
			if language2 not in decisionCounts[language1]:
				decisionCounts[language1][language2] = [0, 0]
			
			decisionCounts[language1][language2][0] += 1
			
			if self.trainLabels[i] == 1:
				decisionCounts[language1][language2][1] += 1
	
		return decisionCounts


	# Once all decisions are counted, computes decision-based language pair
	# similarity using counts of positive and all decisions.
	def computeTrainLanguageSimilarity(self, allExamples, decisionCounts):
		decisionSimilarities = []
		
		for i, (form1, form2, language1, language2, meaningIndex) in enumerate(allExamples[constants.TRAIN]):
			decisionSimilarities.append(decisionCounts[language1][language2][1] / decisionCounts[language1][language2][0])

		return decisionSimilarities
	
	
	# Computes the index of a language pair in a binary language pair feature
	# set. If count is the number of languages, index1 is the index of the first
	# language in the languages list, and index2 is the index of the second
	# language in the languages list, then the index of the pair is computed as
	# follows:
	def computeIndex(self, count, index1, index2):
		return int((count * (count - 1) / 2) - ((count - index1) * (count - index1 - 1) / 2) + (index2 - index1) - 1)
	
	
	# Counts possible language pairs.
	def countLanguageFeatures(self, languages):
		return int(len(languages) * (len(languages) + 1) / 2)
	
	
	# Retrieves indices of the two languages, returns them sorted in an
	# ascending order.
	def getLanguageIndices(self, languages, language1, language2):
		index1 = languages.index(language1)
		index2 = languages.index(language2)
		
		if index1 < index2:
			return index1, index2
		else:
			return index2, index1


	### Edit Operations ###
	# Extracts all edit operations (insertions, deletions, replacements and
	# matches) from positive training examples, stores counts in a matrix.
	def extractEditOps(self, allExamples, allLabels):
		dimensions = constants.LAST - constants.FIRST + 3
		operations = numpy.zeros((dimensions, dimensions))
		
		for index, label in enumerate(allLabels[constants.TRAIN]):
			if label == 1:
				(form1, form2, language1, language2, meaningIndex) = allExamples[constants.TRAIN][index]
				operations = numpy.add(operations, self.exampleLetterFeature(form1, form2))

		return operations
	
	
	# For each example, appends a set of letter correspondence features.
	def appendLetterFeatures(self, allExamples, allLabels, preprocessor = None):
		for purpose, examples in allExamples.iteritems():
			letterFeatures = []
				
			for index, (form1, form2, language1, language2, meaningIndex) in enumerate(examples):
				if preprocessor:
					form1 = self.preprocess(form1, preprocessor)
					form2 = self.preprocess(form2, preprocessor)
				
				operations = self.exampleLetterFeature(form1, form2)
				indices = numpy.triu_indices_from(operations)
				letterFeatures.append(numpy.asarray(operations[indices]))

			letterFeatures = numpy.array(letterFeatures)
			
			self.stackExamples(purpose, letterFeatures)
			self.setLabels(purpose, numpy.array(allLabels[purpose]))


	# For each example, appends a set of letter correspondence features. Letter
	# correspondences are not global, but rather language-group specific.
	def appendGroupLetterFeatures(self, allExamples, allLabels):
		groupCount = len(constants.LANGUAGE_GROUPS)
		groupPairCount = int(groupCount * (groupCount + 1) / 2)
		
		# Formats the language-group correspondence in a more practical way.
		groups = {}
		for group in constants.LANGUAGE_GROUPS:
			for language in group:
				groups[language] = group
		
		for purpose, examples in allExamples.iteritems():
			letterFeatures = []
			
			for index, (form1, form2, language1, language2, meaningIndex) in enumerate(examples):
				operations = self.exampleLetterFeature(form1, form2)
				indices = numpy.triu_indices_from(operations)
				features = numpy.asarray(operations[indices])
				
				letterFeature = []
				
				for i in range(groupCount):
					for j in range(i, groupCount):
						if i == language1 and j == language2:
							letterFeature.extend(features)
						else:
							letterFeature.extend([0.0] * len(features))
		
				letterFeatures.append(numpy.array(letterFeature))

			self.stackExamples(purpose, numpy.array(letterFeatures))
			self.setLabels(purpose, numpy.array(allLabels[purpose]))
	

	# Given two words, extracts all letter correspondence features by aligning
	# the two forms.
	def exampleLetterFeature(self, form1, form2):
		# Adds one dimensions for a space, and another for nothing (i.e.,
		# insertion/deletion).
		dimensions = constants.LAST - constants.FIRST + 3
		space = dimensions - 2
		nothing = dimensions - 1
		
		operations = numpy.zeros((dimensions, dimensions))

		for (tag, i, j, m, n) in Levenshtein.opcodes(form1, form2):
			# Insertion.
			if tag == constants.INSERT:
				for o in range(m, n):
					letter = ord(form2[o]) - constants.FIRST if ord(form2[o]) >= constants.FIRST else space
					operations[nothing][letter] += 1
					operations[letter][nothing] += 1
		
			# Deletion, equality, or replacement.
			else:
				o = m
				for k in range(i, j):
					if tag == constants.DELETE:
						letter = ord(form1[k]) - constants.FIRST if ord(form1[k]) >= constants.FIRST else space
						operations[nothing][letter] += 1
						operations[letter][nothing] += 1
				
					elif tag == constants.EQUAL:
						letter = ord(form1[k]) - constants.FIRST if ord(form1[k]) >= constants.FIRST else space
						operations[letter][letter] += 1
						
					elif tag == constants.REPLACE:
						letter1 = ord(form1[k]) - constants.FIRST if ord(form1[k]) >= constants.FIRST else space
						letter2 = ord(form2[o]) - constants.FIRST if ord(form2[o]) >= constants.FIRST else space
						operations[letter1][letter2] += 1
						operations[letter2][letter1] += 1
		
					o += 1

		return operations
	
	
	### Feature Extraction ###
	# Uses the provided test function to compare wordforms in each word pair and
	# assign a value based on the comparison.
	def appendWordSimilarityFeatures(self, allExamples, allLabels, tests, preprocessor = None):
		for purpose, examples in allExamples.iteritems():
			wordFeatures = []
			
			for i, (form1, form2, language1, language2, meaningIndex) in enumerate(examples):
				if preprocessor:
					form1 = self.preprocess(form1, preprocessor)
					form2 = self.preprocess(form2, preprocessor)

				testValues = [test(form1, form2) for test in tests]
				wordFeatures.append(testValues)
		
			self.stackExamples(purpose, numpy.array(wordFeatures))
			self.setLabels(purpose, numpy.array(allLabels[purpose]))
	

	# Returns, for each meaning, a list of language-sorted cognate group label
	# indices for the test dataset.
	def extractGroupLabels(self, cognateSets, wordforms, testMeanings, testLanguages):
		groupLabels = OrderedDict()
		
		for meaningIndex in testMeanings:
			labels = [-1] * len(wordforms[meaningIndex])
			keys = wordforms[meaningIndex].keys()
			
			for clusterIndex, entries in cognateSets[meaningIndex].iteritems():
				for (wordform, languageIndex) in entries:
					index = keys.index(languageIndex)
					labels[index] = clusterIndex
	
			groupLabels[meaningIndex] = []

			for index, label in enumerate(labels):
				languageIndex = keys[index]

				if (languageIndex in testLanguages):
					groupLabels[meaningIndex].append(label)

		return groupLabels
	
	
	### Word Preprocessing ###
	# Preprocesses the word before features are extracte. For example, the
	# Dolgopolsky's preprocessor converts each letter of the input into one of
	# the 12 sound classes.
	def preprocess(self, form, preprocessor):
		return "".join([preprocessor[char] if char in preprocessor else "" for char in form])


	### Word Similarity Measures ###
	# Returns 1 if at least one letter is shared between the two words.
	def sharedLetter(self, form1, form2):
		for char in form1:
			if char in form2:
				return 1.0
		return 0.0


	# Checks if the two wordforms are identical.
	def identicalWords(self, form1, form2):
		return float(form1 == form2) if (len(form1) * len(form2) > 0) else 0.0

	
	# Checks if the two wordforms have an identical prefix that is at least 4
	# characters long.
	def identicalPrefix(self, form1, form2):
		return float(self.LCPLength(form1, form2) > 3)
	
	
	# Checks if the two wordforms have the same first letter.
	def identicalFirstLetter(self, form1, form2):
		return float(form1[0] == form2[0]) if (len(form1) * len(form2) > 0) else 0.0

	
	# Computes minimum edit distance between the two wordforms. Here, all edit
	# operations have a cost of 1.
	def basicMED(self, form1, form2):
		return float(Levenshtein.distance(form1, form2)) if (len(form1) * len(form2) > 0) else 1.0
	
	
	# Computes normalized minimum edit distance.
	def basicNED(self, form1, form2):
		return self.basicMED(form1, form2) / self.longerWordLen(form1, form2) if (len(form1) * len(form2) > 0) else 1.0
	
	
	# Computes the Jaro distance between the two words.
	def jaroDistance(self, form1, form2):
		return Levenshtein.jaro(form1, form2) if (len(form1) * len(form2) > 0) else 0.0
	
	
	# Computes the Jaro-Winkler distance between the two words.
	def jaroWinklerDistance(self, form1, form2):
		return Levenshtein.jaro_winkler(form1, form2, 0.1) if (len(form1) * len(form2) > 0) else 0.0
	
	
	# Computes the length of the longest common prefix of the two wordforms.
	def LCPLength(self, form1, form2):
		return float(len(os.path.commonprefix([form1, form2])))
	
	
	# Computes the length of the longest common prefix divided by the length of
	# the longer word.
	def LCPRatio(self, form1, form2):
		return self.LCPLength(form1, form2) / self.longerWordLen(form1, form2) if (len(form1) * len(form2) > 0) else 0.0
	
	
	# Computes the length of the longest common subsequence of the two
	# wordforms.
	def LCSLength(self, form1, form2):
		lengths = [[0 for j in range(len(form2) + 1)] for i in range(len(form1) + 1)]
		
		for i, char1 in enumerate(form1):
			for j, char2 in enumerate(form2):
				if char1 == char2:
					lengths[i + 1][j + 1] = lengths[i][j] + 1
				else:
					lengths[i + 1][j + 1] = max(lengths[i + 1][j], lengths[i][j + 1])
	
		return float(lengths[len(form1)][len(form2)])
	
	
	# Computes the longest common subsequence ratio (Melamed, 1999).
	def LCSR(self, form1, form2):
		return self.LCSLength(form1, form2) / self.longerWordLen(form1, form2) if (len(form1) * len(form2) > 0) else 0.0

	
	# Computes Dice's coefficient based on shared bigrams.
	def bigramDice(self, form1, form2):
		return self.ngramDice(2, form1, form2)
	
	
	# Computes Dice's coefficient based on shared trigrams.
	def trigramDice(self, form1, form2):
		return self.ngramDice(3, form1, form2)
	
	
	# A variant of Dice's coefficient based on shared extended bigrams (Brew &
	# McKelvie, 1996).
	def xBigramDice(self, form1, form2):
		if len(form1) < 3 or len(form2) < 3:
			return 0.0
		else:
			return 2 * self.commonXBigramNumber(form1, form2) / (len(form1) + len(form2) - 4)
	
	
	# A variant of Dice's coefficient based on shared extended bigrams and the
	# distance between positions of each shared exteded bigram in the two
	# wordforms. Each shared bigram thus contributes not 2 to the numerator, but
	# rather 2 / (1 + (pos(x) + pos(y))^2), where x and y are the two wordforms
	# (Brew & McKelvie, 1996).
	def xxBigramDice(self, form1, form2):
		if len(form1) < 3 or len(form2) < 3:
			return 0.0
		else:
			positions1, positions2 = self.commonNgramPositions(self.xBigrams(form1), self.xBigrams(form2))

			weights = 0.0
			for i, pos1 in enumerate(positions1):
				weights += 2 / (1 + math.pow(pos1 - positions2[i], 2))
			
			return weights / (len(form1) + len(form2) - 4)
	
	
	# Computes Dice's coefficient based on n-grams of the two wordforms, where
	# s = 2z / x + y (s: similarity, z: number of shared n-grams, x: number of
	# n-grams in the first word, and y: number of n-grams in the second word.
	def ngramDice(self, n, form1, form2):
		if len(form1) < n or len(form2) < n:
			return 0.0
		else:
			return 2 * self.commonNgramNumber(n, form1, form2) / (len(form1) + len(form2) - 2 * (n - 1))
	

	# Computes the number of letters the two words share.
	def commonLetterNumber(self, form1, form2):
		return self.commonNgramNumber(1, form1, form2)


	# Computes the number of bigrams the two words share.
	def commonBigramNumber(self, form1, form2):
		return self.commonNgramNumber(2, form1, form2)
	
	
	# Computes the number of trigrams the two words share.
	def commonTrigramNumber(self, form1, form2):
		return self.commonNgramNumber(3, form1, form2)
	
	
	# Computes the number of extended bigrams the two words share.
	def commonXBigramNumber(self, form1, form2):
		commonXBigrams = self.commonNgrams(self.xBigrams(form1), self.xBigrams(form2))
		return float(len(commonXBigrams))
	
	
	# Computes the number of n-grams the two words share.
	def commonNgramNumber(self, n, form1, form2):
		commonNgrams = self.commonNgrams(self.ngrams(n, form1), self.ngrams(n, form2))
		return float(len(commonNgrams))
	
	
	# Computes the ratio of shared letters of the two words.
	def commonLetterRatio(self, form1, form2):
		return self.commonNgramRatio(1, form1, form2)
	
	
	# Computes the ratio of shared bigrams of the two words.
	def commonBigramRatio(self, form1, form2):
		return self.commonNgramRatio(2, form1, form2)
	
	
	# Computes the ratio of shared trigrams of the two words.
	def commonTrigramRatio(self, form1, form2):
		return self.commonNgramRatio(3, form1, form2)
	
	
	# Computes the ratio of shared extended bigrams of the two words.
	def commonXBigramRatio(self, form1, form2):
		bigramCount = self.longerWordLen(form1, form2) - 2
		return self.commonXBigramNumber(form1,form2) / bigramCount if bigramCount > 0 else 0.0
	

	# Computes the pair's shared n-gram ratio by dividing the number of shared
	# n-grams of the two wordforms by the number of n-grams in the longer word.
	def commonNgramRatio(self, n, form1, form2):
		ngramCount = self.longerWordLen(form1, form2) - (n - 1)
		return self.commonNgramNumber(n, form1,form2) / ngramCount if ngramCount > 0 else 0.0
	
	
	# Computes the length of the longer of the two words.
	def longerWordLen(self, form1, form2):
		return float(len(form1)) if len(form1) > len(form2) else float(len(form2))
	
	
	# Computes the length of the shorter of the two words.
	def shorterWordLen(self, form1, form2):
		return float(len(form1)) if len(form1) < len(form2) else float(len(form2))
	
	
	# Computes the average word length.
	def averageWordLen(self, form1, form2):
		return float((len(form1) + len(form2)) / 2)
	
	
	# Computes the absolute difference between the lengths of the two words.
	def wordLenDifference(self, form1, form2):
		return float(abs(len(form1) - len(form2)))
	
	
	# Computes the relative word length difference between the two words.
	def wordLenDifferenceRatio(self, form1, form2):
		return self.wordLenDifference(form1, form2) / self.longerWordLen(form1, form2) if (len(form1) > 0 or len(form2) > 0) else 0.0
	

	# Generates a list of the word's n-grams.
	def ngrams(self, n, word):
		return [word[i : i + n] for i in range(len(word) - n + 1)]
	
	
	# Generates a list of extended bigrams (formed by deleting the middle letter
	# from a three-letter substring).
	def xBigrams(self, word):
		return [word[i] + word[i + 2] for i in range(len(word) - 2)]
	
	
	# Given two n-gram lists, creates a single list that contains all common
	# ngrams.
	def commonNgrams(self, ngrams1, ngrams2):
		ngrams2 = ngrams2[:]
		ngrams = []
	
		for ngram in ngrams1:
			if ngram in ngrams2:
				ngrams.append(ngram)
				ngrams2.remove(ngram)

		return ngrams
	
	
	# Finds positions of shared n-grams within the two wordforms. When the same
	# n-gram appears multiple times in a word, preference is given to the n-gram
	# closer to the beginning of the word.
	def commonNgramPositions(self, ngrams1, ngrams2):
		ngrams = self.commonNgrams(ngrams1, ngrams2)
		
		positions1 = []
		positions2 = []
		
		for ngram in ngrams:
			for i, ngram1 in enumerate(ngrams1):
				if ngram == ngram1 and i not in positions1:
					positions1.append(i)
					break
	
			for j, ngram2 in enumerate(ngrams2):
				if ngram == ngram2 and j not in positions2:
					positions2.append(j)
					break
		
		return positions1, positions2
	
	
	### Baseline Tests ###
	# Returns the wordform itself.
	def getWordform(self, wordform):
		return wordform
	
	
	# Returns the first letter of the wordform.
	def getFirstLetter(self, wordform):
		return wordform[0]
	
	
	# Returns None for wordforms shorter than four characters, and the first
	# four characters of the wordform otherwise.
	def getPrefix(self, wordform):
		if len(wordform) < 4:
			return None
		else:
			return wordform[ : 4]


	### Formatting ###
	# Appends additional features to existing examples, or sets the new features
	# as current examples if no examples exist yet.
	def stackExamples(self, purpose, extension):
		if purpose == constants.TRAIN:
			self.trainExamples = numpy.column_stack((self.trainExamples, extension)) if numpy.any(self.trainExamples) else extension
		else:
			self.testExamples = numpy.column_stack((self.testExamples, extension)) if numpy.any(self.testExamples) else extension


	# Sets labels.
	def setLabels(self, purpose, labels):
		if purpose == constants.TRAIN and not numpy.any(self.trainLabels):
			self.trainLabels = labels
		elif purpose == constants.TEST and not numpy.any(self.testLabels):
			self.testLabels = labels