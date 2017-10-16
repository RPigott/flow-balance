import numpy as np
import pandas as pd

import os
ldir = os.path.dirname(__file__)

# Config Section
fwys = {
  210: {
    'name': 'I210',
    'dirs': ['E', 'W'],
    'range': (22.6, 41.4)
  },
  134: {
    'name': 'SR134',
    'dirs': ['E', 'W'],
    'range': (11.4, 13.5)
  },
  605: {
    'name': 'I605',
    'dirs': ['N', 'S'],
    'range': (25.3, 28.0)
  }
}

lane_order = ['Mainline', 'HOV', 'On Ramp', 'Off Ramp', 'Fwy-Fwy', 'Coll/Dist', 'Conventional Highway']
lane_types = {
	'CD': 'Coll/Dist',
	'CH': 'Conventional Highway',
	'FF': 'Fwy-Fwy',
	'FR': 'Off Ramp',
	'HV': 'HOV',
	'ML': 'Mainline',
	'OR': 'On Ramp'
}

# county_url = \
# 'https://www2.census.gov/geo/docs/reference/codes/files/st06_ca_cou.txt'
# names = ['State', 'State No', 'County No', 'County', 'Code']
df_county = pd.read_csv(os.path.join(ldir, 'maps', 'county-codes.csv'), header = 0)
county_codes = {
	no:name[:-7]
	for no, name in df_county[['County No', 'County']].values
}

# places_url = \
# 'https://www2.census.gov/geo/docs/reference/codes/files/st06_ca_places.txt'
# names = [
	# 'State', 'State No', 'FIPS No', 'Name', 'Type', 'Division', 'County'
# ]
df_places = pd.read_csv(os.path.join(ldir, 'maps', 'place-codes.csv'),
	header = 0, sep = '|')
place_codes = {
	no:name[:-5]
	for no, name in df_places[['FIPS No', 'Name']].values
}

def revise_meta(df_meta):
	# Clean the meta format and drop useless colums
	df_meta = df_meta.rename(columns = {
		'Abs_PM': 'Abs PM',
		'State_PM': 'CA PM',
		'User_ID_1': 'MS ID'
	}).drop(['District', 'User_ID_2', 'User_ID_3', 'User_ID_4'], axis = 1)

	df_meta['Exact'] = False
	df_meta.set_index('ID', inplace = True)

	return df_meta

def rename_locations(df_meta):
	df_meta.replace({
		'City': place_codes,
		'County': county_codes,
		'Type': lane_types
	}, inplace = True)