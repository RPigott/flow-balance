import numpy as np
import pandas as pd
import networkx as nx

import boto3, json, re
from zipfile import ZipFile
from tempfile import TemporaryFile
from collections import defaultdict
from operator import itemgetter

import logging
logger = logging.getLogger(__name__)


# model.zip: 'detectors.json'
# Detectors {id: (pems)
#	Description, Final Position, First Lane, Last Lane, External ID (pems)
#	Start Position, Position, Section ID, ID (model)
# }
# model.zip: 'junctions.json'
# Junctions {id: Outgoing, Incoming, Name, Turns,
#	External ID, Signalized, ID
# }
# model.zip: 'sections.json'
# Sections {id: Origin, External ID, Lanes, Name, Destination, ID}

def lambda_handler(event, context):
	# Retrieve extracted model data, model.zip must have
	s3 = boto3.client('s3')
	with TemporaryFile() as model:
		s3.download_fileobj('flow-balance', 'info/model.zip', model)
		model.seek(0)
		detectors, junctions, sections = get_djs(model)
	
	# Record which detectors appear at all in the model
	with TemporaryFile('w+') as file:
		json.dump(list(detectors), file)
		file.seek(0)
		s3.upload_fileobj(file, 'flow-balance', 'info/tracked.json')

	# Record which detectors form closed FATVs
	df_cfatv = get_fatvs(detectors, junctions, sections)
	with TemporaryFile('w+') as file:
		df_cfatv.to_json(file, orient = 'index')
		file.seek(0)
		s3.upload_fileobj(file, 'flow-balance', 'info/fatvs.json')

def get_djs(model):
	good_ptn = re.compile(r'^7\d+$')
	bad_ptn = re.compile(r'^7131')
	good_det = lambda id: re.match(good_ptn, id) and not re.match(bad_ptn, id)
	with ZipFile(model) as zm:
		with zm.open('detectors.json') as dets:
			detectors = json.load(dets)
			detectors = {int(id): det for id, det in detectors.items() if good_det(id)}

		with zm.open('junctions.json') as junctions:
			junctions = json.load(junctions)
			junctions = {int(id): j for id, j in junctions.items()}

		with zm.open('sections.json') as sections:
			sections = json.load(sections)
			sections = {int(id): s for id, s in sections.items()}
	
	return detectors, junctions, sections


def get_fatvs(detectors, junctions, sections):
	# We need to be able to find detectors by their associated sections
	s2det = defaultdict(list)
	for pid, det in detectors.items():
		s2det[det['Section ID']].append(det)

	# Sections are not the same as edges in the graph,
	# because there may be more than one detector per section.
	# Detectors may be adjacent or in sequence. Adjacent detectors are NOT
	# considered to preserve flow-balance, and will belong to the same FATV.
	sfatvs = {'IN': [], 'OUT': []}
	get_track = itemgetter('First Lane', 'Last Lane')
	get_pid = itemgetter('External ID')
	for s, dets in s2det.items():
		# In the order detectors appear to a vehicle in transit
		ds = sorted(dets, key = itemgetter('Start Position'))
		
		# Detectors are sorted by 'tracks' (lanes spanned)
		tracks = defaultdict(list)
		for d in ds:
			track = get_track(d)
			tracks[track].append(d)

		# If each 'track' spans the section, they are split into spanning sets
		dsets = zip(*tracks.values())
		# We only need the pems id from each
		dsets = [map(get_pid, dset) for dset in dsets]
		# Re-record detectors per section as a list of equivalent detector sets
		s2det[s] = dsets

		# For each spanning set, match with the following spanning set to form a FATV
		for fin, fout in zip(dsets, dsets[1:]):
			sfatvs['IN'].append(fin)
			sfatvs['OUT'].append(fout)

	# Represent the network as a graph
	G = nx.DiGraph()
	# Junctions are the nodes
	G.add_nodes_from(junctions.keys())
	# Sections are the edges
	edges = [
		(s['Origin'], s['Destination'], {'ID': mid, 'detectors': s2det[mid]})
		for mid, s, in sections.items()
	]

	# Start only with sections that have NO detectors
	G.add_edges_from( e for e in edges if not e[2]['detectors'] )
	# Find groups of detectors that have unmetered routes via weakly connected components
	wccs = list(nx.weakly_connected_components(G))
	# Exclude groups that contain unmetered routes to the exterior
	groups = [wcc for wcc in wccs if None not in wcc]
	
	# Complete the graph and extract FATVs
	G.add_edges_from(edges)

	# Locus of final detector sets for each incoming section per group
	fatv_ins = [[G.edges[start, end]['detectors'][-1] for start, end in G.in_edges(group) if start not in group] for group in groups]

	# Locus of initial detector sets for each incoming section per group
	fatv_outs = [[G.edges[start, end]['detectors'][0] for start, end in G.out_edges(group) if end not in group] for group in groups]

	# Match incoming with outgoing
	df_cfatv = pd.DataFrame({
		'IN': fatv_ins,
		'OUT': fatv_outs
	})

	# Append trivial FATVs contained in each section
	df_cfatv = df_cfatv.append(pd.DataFrame(sfatvs).applymap(lambda g: [g]), ignore_index = True)

	# Flatten each group of incoming detectors into list of peers with int values
	flat1 = lambda L: [n for s in L for n in s]
	df_cfatv = df_cfatv.applymap(flat1)
	df_cfatv = df_cfatv.applymap(lambda L: map(int, L))

	return df_cfatv
