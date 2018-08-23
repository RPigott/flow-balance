from PyANGBasic import *
from PyANGKernel import *
from PyANGGui import *
from PyANGAimsun import *

import os, sys, json
import operator as op
  
def ExtractJunctionInformation(model,outputLocation):
	junctions = {}
	for types in model.getCatalog().getUsedSubTypesFromType(model.getType("GKNode")):
		for junctionObj in types.itervalues():
			junction = {}

			junction['ID'] = junctionObj.getId()
			junction['External ID'] = junctionObj.getExternalId()
			junction['Name'] = junctionObj.getName()

			junction['Incoming'] = [section.getId() for section in junctionObj.getEntranceSections()]
			junction['Outgoing'] = [section.getId() for section in junctionObj.getExitSections()]

			turnings = junctionObj.getTurnings()
			junction['Signalized'] = True if junctionObj.getSignals() else False

			junction['Turns'] = []
			for turnObj in turnings:
				turn = {}
				origin = turnObj.getOrigin()
				destination = turnObj.getDestination()

				originObj = model.getCatalog().find(origin.getId())
				numLanesOrigin = len(originObj.getLanes())
				destinationObj = model.getCatalog().find(destination.getId())
				numLanesDest = len(destinationObj.getLanes())

				turn['ID'] = turnObj.getId()
				turn['Origin'] = turnObj.getOrigin().getId()
				turn['Destination'] = turnObj.getDestination().getId()
				turn['Origin From Lane'] = numLanesOrigin - turnObj.getOriginToLane()
				turn['Origin To Lane'] = numLanesOrigin - turnObj.getOriginFromLane()
				turn['Destination From Lane'] = numLanesDest - turnObj.getDestinationToLane()
				turn['Destination To Lane'] = numLanesDest - turnObj.getDestinationFromLane()

				junction['Turns'].append(turn)

			junctions[junction['ID']] = junction

	filename = os.path.join(outputLocation, 'junctions.json')
	with open(filename, 'w') as file:
		json.dump(junctions, file, indent = 2)

	return 0

def ExtractSectionInformation(model,outputLocation):
	translator = GKCoordinateTranslator(model)

	sections = {}
	for types in model.getCatalog().getUsedSubTypesFromType(model.getType("GKSection")):
		for sectionObj in types.itervalues():
			section = {}

			section['ID'] = sectionObj.getId()
			section['External ID'] = sectionObj.getExternalId()
			section['Name'] = sectionObj.getName()
			origin = sectionObj.getOrigin()
			dest = sectionObj.getDestination()
			section['Origin'] = origin.getId() if origin else None
			section['Destination'] = dest.getId() if dest else None

			section['Lanes'] = len(sectionObj.getLanes())

			sections[section['ID']] = section

	filename = os.path.join(outputLocation, 'sections.json')
	with open(filename, 'w') as file:
		json.dump(sections, file, indent = 2)

	return 0

def ExtractDetectorInformation(model,outputLocation):
	detectors = {}
	for types in model.getCatalog().getUsedSubTypesFromType(model.getType("GKDetector")):
		for detectorObj in types.itervalues():
			detector = {}
			detector['ID'] = detectorObj.getId()
			detector['External ID'] = detectorObj.getExternalId()
			detector['Description'] = detectorObj.getDescription()

			startPos = detectorObj.getPosition() * 3.28084
			endPos = startPos + detectorObj.getLength() * 3.28084
			section = detectorObj.getSection()
			sectionObj = model.getCatalog().find(section.getId())
			numLanes = len(sectionObj.getLanes())

			detector['Section ID'] = section.getId()
			detector['First Lane'] = numLanes - detectorObj.getToLane()
			detector['Last Lane'] = numLanes - detectorObj.getFromLane()
			detector['Start Position'] = startPos
			detector['Final Position'] = endPos

			pos = detectorObj.absolutePosition()
			detector['Position'] = map(lambda x: x*3.28084, [pos.x, pos.y, pos.z])

			detectors[detector['External ID']] = detector

	filename = os.path.join(outputLocation, 'detectors.json')
	with open(filename, 'w') as file:
		json.dump(detectors, file, indent = 2)

	return 0
 

gui = GKGUISystem.getGUISystem().getActiveGui()
model = gui.getActiveModel()
print('Load the network successfully!')
outputLocation = os.getcwd()
print outputLocation

ExtractJunctionInformation(model,outputLocation)
ExtractSectionInformation(model, outputLocation)
ExtractDetectorInformation(model, outputLocation)
print 'Done with network extraction!'