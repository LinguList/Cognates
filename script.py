from __future__ import division
import itertools
import operator

import constants
import extractor
import learner
import output
import pairer
import reader



# FUNCTIONS
### Rule-Based Baselines ###
def pairwiseDeduction(measure):
	# Feature extraction
	ext = extractor.Extractor()
	
	if measure == constants.IDENTICAL_WORDS:
		ext.identicalWordsBaseline(prr.examples, prr.labels)
	elif measure == constants.IDENTICAL_PREFIX:
		ext.identicalPrefixBaseline(prr.examples, prr.labels)
	elif measure == constants.IDENTICAL_LETTER:
		ext.identicalFirstLetterBaseline(prr.examples, prr.labels)
	
	predictions = ext.testExamples.reshape((ext.testExamples.shape[0],))

	# Evaluation
	lrn = learner.Learner()
	accuracy = lrn.computeAccuracy(ext.testLabels, predictions)
	F1 = lrn.computeF1(ext.testLabels, predictions)
	report = lrn.evaluatePairwise(ext.testLabels, predictions)
	
	# Reporting
	output.reportPairwiseDeduction(constants.DEDUCERS[measure], prr, accuracy, F1, report)
	output.savePredictions("output/Pairwise " + constants.DEDUCERS[measure] + ".txt", prr.examples[constants.TEST], ext.testExamples, predictions, ext.testLabels)

	return predictions


def groupDeduction(measure):
	# Feature extraction
	ext = extractor.Extractor()
	
	if measure == constants.IDENTICAL_WORDS:
		predictedLabels, predictedSets = ext.identicalWordsGroupBaseline(prr.testMeanings, prr.testLanguages, rdr.wordforms)
	elif measure == constants.IDENTICAL_PREFIX:
		predictedLabels, predictedSets = ext.identicalPrefixGroupBaseline(prr.testMeanings, prr.testLanguages, rdr.wordforms)
	elif measure == constants.IDENTICAL_LETTER:
		predictedLabels, predictedSets = ext.identicalFirstLetterGroupBaseline(prr.testMeanings, prr.testLanguages, rdr.wordforms)

	trueLabels = ext.extractGroupLabels(rdr.cognateSets, rdr.wordforms, prr.testMeanings, prr.testLanguages)
	
	# Evaluation
	lrn = learner.Learner()
	V1scores = {meaningIndex: lrn.computeV1(trueLabels[meaningIndex], predictedLabels[meaningIndex]) for meaningIndex in prr.testMeanings}

	# Reporting
	output.reportGroup(constants.DEDUCERS[measure], V1scores, rdr.meanings)
	output.saveGroup("output/Group " + constants.DEDUCERS[measure] + ".txt", predictedSets)


### Hauer & Kondrak Baselines ###
def HK2011Pairwise():
	# 1st Pass
	# Feature extraction
	ext = extractor.Extractor()
	ext.HK2011Baseline(prr.examples, prr.labels)

#	ext.appendLanguageFeatures(prr.examples, constants.TRAIN, prr.trainLanguages)
#	ext.appendLanguageFeatures(prr.examples, constants.TEST, prr.testLanguages)

	# Learning
	lrn = learner.Learner()
	lrn.initSVM(0.1)
	lrn.fitSVM(ext.trainExamples, ext.trainLabels)
	
	# Prediction
	predictions1 = lrn.predictSVM(ext.testExamples)
	
	# Evaluation
	accuracy = lrn.computeAccuracy(ext.testLabels, predictions1)
	F1 = lrn.computeF1(ext.testLabels, predictions1)
	report = lrn.evaluatePairwise(ext.testLabels, predictions1)
	
	# Reporting
	stage = "HK2011 1st Pass"
	output.reportPairwiseLearning(stage, prr, accuracy, F1, report)
	output.savePredictions("output/" + stage + ".txt", prr.examples[constants.TEST], ext.testExamples, predictions1, ext.testLabels)
	

	# 2nd Pass
	# Feature extraction
	ext.appendLanguageFeatures(prr.examples, constants.TEST, prr.testLanguages)

	# Learning
	lrn = learner.Learner()
	lrn.initSVM(0.001)
	lrn.fitSVM(ext.testExamples, predictions1)
	
	# Prediction
	predictions2 = lrn.predictSVM(ext.testExamples)
	
	# Evaluation
	accuracy = lrn.computeAccuracy(ext.testLabels, predictions2)
	F1 = lrn.computeF1(ext.testLabels, predictions2)
	report = lrn.evaluatePairwise(ext.testLabels, predictions2)
	
	# Reporting
	stage = "HK2011 2nd Pass"
	output.reportPairwiseLearning(stage, prr, accuracy, F1, report)
	output.savePredictions("output/" + stage + ".txt", prr.examples[constants.TEST], ext.testExamples, predictions2, ext.testLabels)


	# Significance
	print constants.SIGNIFICANCE.format(lrn.computeMcNemarSignificance(ext.testLabels, predictions1, predictions2))


	return ext, lrn


def HK2011Clustering(ext, lrn):
	# Feature extraction
	trueLabels = ext.extractGroupLabels(rdr.cognateSets, rdr.wordforms, prr.testMeanings, prr.testLanguages)
	
	# Threshold
	threshold = lrn.computeDistanceThreshold(constants.SVM, rdr.wordforms, prr.testMeanings, prr.testLanguages, ext.HK2011ExtractorFull, trueLabels)

	# Learning
	predictedLabels, predictedSets, clusterCounts, clusterDistances = lrn.cluster(constants.SVM, constants.T1, rdr.wordforms, prr.testMeanings, prr.testLanguages, ext.HK2011ExtractorFull)

	# Evaluation
	V1scores = {meaningIndex: lrn.computeV1(trueLabels[meaningIndex], predictedLabels[meaningIndex]) for meaningIndex in prr.testMeanings}

	# Reporting
	output.reportCluster(V1scores, clusterCounts, clusterDistances, rdr.meanings)
	output.saveGroup("output/Clustering.txt", predictedSets)


### My Method ###
def completeFeatureSelection():
	# Feature extraction
	ext = extractor.Extractor()

	features = [
		("identicalWords", ext.identicalWords),
		("identicalPrefix", ext.identicalPrefix),
		("identicalFirstLetter", ext.identicalFirstLetter),
		("basicMED", ext.basicMED),
		("basicNED", ext.basicNED),
		("jaroDistance", ext.jaroDistance),
		("jaroWinklerDistance", ext.jaroWinklerDistance),
		("LCPLength", ext.LCPLength),
		("LCPRatio", ext.LCPRatio),
		("LCSLength", ext.LCSLength),
		("LCSR", ext.LCSR),
		("bigramDice", ext.bigramDice),
		("trigramDice", ext.trigramDice),
		("xBigramDice", ext.xBigramDice),
		("xxBigramDice", ext.xxBigramDice),
		("commonLetterNumber", ext.commonLetterNumber),
		("commonBigramNumber", ext.commonBigramNumber),
		("commonTrigramNumber", ext.commonTrigramNumber),
		("commonXBigramNumber", ext.commonXBigramNumber),
		("commonBigramRatio", ext.commonBigramRatio),
		("commonLetterRatio", ext.commonLetterRatio),
		("commonTrigramRatio", ext.commonTrigramRatio),
		("commonXBigramRatio", ext.commonXBigramRatio),
		("longerWordLen", ext.longerWordLen),
		("shorterWordLen", ext.shorterWordLen),
		("averageWordLen", ext.averageWordLen),
		("wordLenDifference", ext.wordLenDifference),
		("wordLenDifferenceRatio", ext.wordLenDifferenceRatio)
	]
	
	# Feature selection
	with open("output/Measures.txt", "wb") as output:
		for i in range(1, len(features) + 1):
			for subset in itertools.combinations(features, i):
				IDs = [ID for (ID, method) in subset]
				methods = [method for (ID, method) in subset]
				
				ext.cleanup()
				ext.batchCompute(prr.examples, prr.labels, methods)

				coefficients, F1, accuracy, report = learn(ext, 0.001)
	
				print "{0}\n{1}\n{2}".format(IDs, coefficients, F1)
				output.write("{0}\t{1}\t{2}\n".format(IDs, F1, coefficients))


def groupFeatureSelection():
	# Feature extraction
	ext = extractor.Extractor()

	featureSets = [
		[("identicalWords", ext.identicalWords),
		("identicalPrefix", ext.identicalPrefix),
		("identicalFirstLetter", ext.identicalFirstLetter)],

		[("basicMED", ext.basicMED),
		("basicNED", ext.basicNED)],

		[("jaroDistance", ext.jaroDistance),
		("jaroWinklerDistance", ext.jaroWinklerDistance)],

		[("LCPLength", ext.LCPLength),
		("LCPRatio", ext.LCPRatio)],

		[("LCSLength", ext.LCSLength),
		("LCSR", ext.LCSR)],

		[("bigramDice", ext.bigramDice),
#		("commonBigramNumber", ext.commonBigramNumber),
		("commonBigramRatio", ext.commonBigramRatio)],

#		[("trigramDice", ext.trigramDice),
#		("commonTrigramNumber", ext.commonTrigramNumber),
#		("commonTrigramRatio", ext.commonTrigramRatio)],

#		[("xBigramDice", ext.xBigramDice),
#		("xxBigramDice", ext.xxBigramDice),
#		("commonXBigramNumber", ext.commonXBigramNumber),
#		("commonXBigramRatio", ext.commonXBigramRatio)],

		[("commonLetterNumber", ext.commonLetterNumber),
		("commonLetterRatio", ext.commonLetterRatio)],

#		[("longerWordLen", ext.longerWordLen),
#		("shorterWordLen", ext.shorterWordLen),
		[("averageWordLen", ext.averageWordLen)],

		[("wordLenDifference", ext.wordLenDifference),
		("wordLenDifferenceRatio", ext.wordLenDifferenceRatio)]
	]

	# Feature selection
	with open("output/Measures 8-11.txt", "wb") as output:
		for i in range(8, len(featureSets) + 1):
			for sets in itertools.combinations(featureSets, i):
				for product in itertools.product(*sets):
					IDs = [ID for (ID, method) in product]
					methods = [method for (ID, method) in product]
			
					ext.cleanup()
					ext.batchCompute(prr.examples, prr.labels, methods)
					
					coefficients, F1, accuracy, report = learn(ext, 0.001)
					
					print "{0}\n{1}\n{2}".format(IDs, coefficients, F1)
					output.write("{0}\t{1}\t{2}\n".format(IDs, F1, coefficients))


def treeFeatureSelection():
	# Feature extraction
	ext = extractor.Extractor()
	
	features = [ext.identicalWords, ext.identicalPrefix, ext.identicalFirstLetter, ext.basicMED, ext.basicNED, ext.jaroDistance, ext.jaroWinklerDistance, ext.LCPLength, ext.LCPRatio, ext.LCSLength, ext.LCSR, ext.bigramDice, ext.trigramDice, ext.xBigramDice, ext.xxBigramDice, ext.commonLetterNumber, ext.commonBigramNumber, ext.commonTrigramNumber, ext.commonXBigramNumber, ext.commonBigramRatio, ext.commonLetterRatio, ext.commonTrigramRatio, ext.commonXBigramRatio, ext.longerWordLen, ext.shorterWordLen, ext.averageWordLen, ext.wordLenDifference, ext.wordLenDifferenceRatio]

	ext.batchCompute(prr.examples, prr.labels, features)
	
	# Feature selection
	lrn = learner.Learner()
	lrn.initForest(250, 0)
	lrn.fitForest(ext.trainExamples, ext.trainLabels)
	importances, indices = lrn.getForestImportances()
	
	# Reporting
	for i in range(len(features)):
		print("Feature {0}: {1:.4f}".format(indices[i], importances[indices[i]]))


def editOperations():
	# Feature extraction
	ext = extractor.Extractor()
	operations = ext.extractEditOps(prr.examples, prr.labels)
	
	for tag, correspondences in operations.iteritems():
		print tag
		
		items = sorted(correspondences.items(), key = operator.itemgetter(1), reverse = True)
		for i, (entry, count) in enumerate(items):
			if i < 5:
				print entry, count
			else:
				break


def negativeElimination():
	# Feature extraction
	ext = extractor.Extractor()
	ext.batchCompute(prr.examples, prr.labels, ext.negativeMeasure)
	
	predictions = ext.testExamples.reshape((ext.testExamples.shape[0],))

	# Evaluation
	lrn = learner.Learner()
	accuracy = lrn.computeAccuracy(ext.testLabels, predictions)
	F1 = lrn.computeF1(ext.testLabels, predictions)
	report = lrn.evaluatePairwise(ext.testLabels, predictions)
	
	# Reporting
	stage = "Negative Elimination"
	output.reportPairwiseDeduction(stage, prr, accuracy, F1, report)
	output.savePredictions("output/" + stage + ".txt", prr.examples[constants.TEST], ext.testExamples, predictions, ext.testLabels)
	
	return predictions


def pairwiseLearning():
	# Feature extraction
	ext = extractor.Extractor()
	ext.batchCompute(prr.examples, prr.labels, ext.allMeasures)
	
	# Learning
	coefficients, F1, accuracy, report = learn(ext, 0.00005)

	# Reporting
	stage = "Pairwise Learning"
	output.reportPairwiseLearning(stage, prr, accuracy, F1, report)


def learn(ext, C):
	# Learning
	lrn = learner.Learner()
	lrn.initLogisticRegression(C)
	lrn.fitLogisticRegression(ext.trainExamples, ext.trainLabels)
	
	# Prediction
	predictions = lrn.predictLogisticRegression(ext.testExamples)
	
	# Evaluation
	accuracy = lrn.computeAccuracy(ext.testLabels, predictions)
	F1 = lrn.computeF1(ext.testLabels, predictions)
	report = lrn.evaluatePairwise(ext.testLabels, predictions)
	
	return lrn.LR.coef_, F1, accuracy, report



# FLOW
# Reading
rdr = reader.Reader(constants.IN)
rdr.read()

trainMeanings = [i for i in range(1, constants.MEANING_COUNT + 1) if (i % 10 != 0 and i % 10 != 5)]
devMeanings = [i for i in range(1, constants.MEANING_COUNT + 1) if i % 10 == 5]
testMeanings = [i for i in range(1, constants.MEANING_COUNT + 1) if i % 10 == 0]


# Pairing
prr = pairer.Pairer()
prr.pairBySpecificMeaning(rdr.cognateCCNs, rdr.dCognateCCNs, trainMeanings, devMeanings)


# Learning