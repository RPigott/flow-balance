import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as md

import networkx as nx

import os, sys, re, json
from collections import defaultdict
from operator import attrgetter, itemgetter

ldir = os.path.dirname(__file__)

# Read in junctions.json ripped from Aimsun model by GraphExtract.py
with open(os.path.join(ldir, 'model', 'junctions.json'), 'r') as file:
	junctions = json.load(file)
junctions = {int(mid):j for mid, j in junctions.items()}

# Read in sections.json ripped from Aimsun model by GraphExtract.py
with open(os.path.join(ldir, 'model', 'sections.json'), 'r') as file:
	sections = json.load(file)
sections = {int(mid):s for mid, s in sections.items()}

# function for labelling detectors not to include
def bad_det(d):
	return d['External ID'].startswith('7131') # These are not PeMS detectors!

ptn = r'^7[0-9]+$' # PeMS detectors have names that begin with '7' and are all numbers
with open(os.path.join(ldir, 'model', 'detectors.json'), 'r') as file:
	detectors = json.load(file)
detectors = {int(pid):d for pid, d in detectors.items() if re.match(ptn, pid) and not bad_det(d)}

# Organize valid detectors so we can find them by their associated section.
# There may be more than one detector per section, sections will be split into links when we build the graph
s2d = defaultdict(list)
for pid, d in detectors.items():
	s2d[d['Section ID']].append(d)

sfatvs = {'IN': [], 'OUT': []}
# We need to separate detectors by the lanes they span.
# Adjacent detectors are NOT considered to conserve flow-balance, and will belong to the same FATV
get_track = itemgetter('First Lane', 'Last Lane')
get_pid = itemgetter('External ID')
for s, ds in s2d.items():
	ds = sorted(ds, key = itemgetter('Start Position')) # Process detectors in the order they appears to vehicles
	tracks = defaultdict(list)
	for d in ds: # Split detectors on a section by their 'tracks' (lanes spanned).
		track = get_track(d)
		tracks[track].append(d)
	dsets = zip(*tracks.values()) # Assume each 'track' has an equal number of detectors and split into sets of adjacent detectors
	dsets = [map(get_pid, dset) for dset in dsets]
	s2d[s] = dsets # Store track sets by section for later
	# Split section into links assuming tracks span all lanes by combining adjacent detectors.
	for fin, fout in zip(dsets, dsets[1:]):
		sfatvs['IN'].append(fin)
		sfatvs['OUT'].append(fout)

G = nx.DiGraph()
# Supply all junctions as nodes
G.add_nodes_from(junctions.keys())
# Supply all sections as edges
edges = [
	(s['Origin'], s['Destination'],
		{'ID': mid,
		 'detectors': s2d[mid], # Associate detectors in their track sets
		}
	) for mid, s in sections.items()]

G.add_edges_from( e for e in edges if not e[2]['detectors'] ) # Add only edges that have NO detectors
wccs = list(nx.weakly_connected_components(G)) # WCC used to collapse FATVs
# Identify all node groups that do not have unmetered connections to the exterior (None node)
groups = [wcc for wcc in wccs if None not in wcc]
G.add_edges_from(edges) # Complete the graph representation by adding in remaining edges

get_pid = itemgetter('External ID')
# Create FATV frame from fatvs joining multiple sections
df_cfatv = pd.DataFrame({
	# The input of each FATV is the locus of final track sets from incoming sections
	'IN': [[G.edge[start][end]['detectors'][-1] for start, end in G.in_edges_iter(group) if start not in group]
		 for group in groups], # FATVs cannot be formed across junctions that have unmetered connections to the exterior

	# The output of each FATV is the locus of initial track sets from outgoing sections
	'OUT': [[G.edge[start][end]['detectors'][0] for start, end in G.out_edges_iter(group) if end not in group]
		 for group in groups]
}).append(pd.DataFrame(sfatvs).applymap(lambda g: [g]), ignore_index = True) # Append 'trivial' FATVs that join intrasectional track sets

# Flatten track sets into detector groups
df_cfatv = df_cfatv.applymap(lambda L: [n for s in L for n in s])

# Convert track ids to ints for easier indexing
df_cfatv = df_cfatv.applymap(lambda L: map(int, L))

# Write to file for reference
df_cfatv.to_json(os.path.join(ldir, 'model', 'fatvs.json'), orient = 'index')
