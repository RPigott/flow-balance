from pykml import parser
import os
import numpy as np
import pandas as pd

from utils import revise_meta, rename_locations

import re, operator
import IPython

ldir = os.path.dirname(__file__)

with open(os.path.join(ldir, 'maps', 'VDS-locations.kml'), 'r') as file:
	tree = parser.parse(file)

root = tree.getroot()
nsmap = root.nsmap
vds_ptn = r'^[0-9]{6}(.0)?$'

locations = {}
for pm in root.findall(".//Placemark", nsmap):
	vds = pm.name.text
	if not vds: continue
	if re.match(vds_ptn, vds):
		lat = pm.find(".//*[@name='lat']").value
		lon = pm.find(".//*[@name='long']").value
	else:
		vds = pm.find(".//*[@name='ID']").value
		lat = pm.find(".//*[@name='lat']").value
		lon = pm.find(".//*[@name='lon']").value

	vds = int(float(vds))
	locations[vds] = float(lat), float(lon)

vdss = []
lats = []
lons = []
for vds, (lat, lon) in sorted(locations.items()):
	vdss.append(vds)
	lats.append(lat)
	lons.append(lon)

df_locations = pd.DataFrame({
	'Latitude': lats,
	'Longitude': lons
	},
	index = vdss
)
df_locations['Exact'] = True

# day, df_meta = pdr.download('meta')
# df_meta = revise_meta(df_meta)
# rename_locations(df_meta)
# 
# df_meta.update(df_locations)
# cols = ['Fwy', 'Dir', 'Name', 'City', 'County', 'Type', 'Lanes', 'Length',
# 'MS ID', 'Abs PM', 'CA PM', 'Latitude', 'Longitude', 'Exact']
# df_meta = df_meta[cols]

# loc = ['Latitude', 'Longitude']
# for fwy, fdata in fwys.items():
	# for dir in fdata['dirs']:
		# df_meta[
			# (df_meta['Fwy'] == fwy) & (df_meta['Dir'] == dir)
		# ].dropna(subset = loc, how = 'any').to_csv('maps/full/{}-{}.csv'.format(fwy, dir))
# df_meta[~df_meta['Fwy'].isin(fwys.keys())].dropna(subset = loc, how = 'any').to_csv('maps/full/other.csv')

# for fwy, fdata in fwys.items():
	# for dir in fdata['dirs']:
		# lo, hi = fdata['range']
		# df_meta[
			# (df_meta['Fwy'] == fwy) & (df_meta['Dir'] == dir) & (df_meta['Abs PM'] >= lo) & (df_meta['Abs PM'] <= hi)
		# ].dropna(subset = loc, how = 'any').to_csv('maps/corr/{}-{}.csv'.format(fwy, dir))
