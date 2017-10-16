"""
Defines the diagnostics criteria for flow-balance
"""

import numpy as np
import pandas as pd
import datetime, dateparser
import os
from operator import itemgetter, attrgetter
ldir = os.path.dirname(__file__)

import logging
logger = logging.getLogger(__name__)

def diagnose(df_meta, df_day, df_cfatv):
    df_piv = df_day.pivot('Timestamp', 'Station', 'Flow')
    
    # Only utilize data from detectors that exceed 50% observed data
    obv = df_day.pivot('Timestamp', 'Station', 'Observed').mean() > 50
    unobv = obv[~obv].index
    df_piv[unobv] = np.nan
    
    # Identify imbalanced detectors
    df_cfatv['ERR'] = np.nan
    df_cfatv['DIF'] = np.nan
    df_cfatv['VOL'] = np.nan
    for idx in df_cfatv.index:
        ins, outs = df_cfatv.loc[idx, ['IN', 'OUT']]
        try:
            ins = df_piv[ins].sum(skipna = False).sum(skipna = False)
            outs = df_piv[outs].sum(skipna = False).sum(skipna = False)
        except KeyError as e:
            logger.debug("skipping {}".format(idx))
            ins = np.nan
            outs = np.nan
    
        df_cfatv.loc[idx, 'DIF'] = ins - outs
        df_cfatv.loc[idx, 'VOL'] = ins + outs
        df_cfatv.loc[idx, 'ERR'] = abs(ins - outs) / (ins + outs)
    imb = df_cfatv[df_cfatv['ERR'] > 0.05]
    
    imp1, imp2 = [], []
    for idx, fatv in df_cfatv[df_cfatv['ERR'] > 0.025].iterrows():
        neighbors = {}
        for det in fatv['IN']:
            for nidx in df_cfatv[df_cfatv['OUT'].map(lambda ds: det in ds)].index:
                neighbors[det] = nidx
        for det in fatv['OUT']:
            for nidx in df_cfatv[df_cfatv['IN'].map(lambda ds: det in ds)].index:
                neighbors[det] = nidx
    
        for det, neighbor in neighbors.items():
            pair = df_cfatv.loc[[idx, neighbor]]
            if pair.loc[neighbor]['ERR'] < 0.01:
                continue
            temp = pair.sum()
            temp['ERR'] = abs(temp['DIF'])/temp['VOL']
    
            if temp['ERR'] < 0.15 * fatv['ERR']:
                if det in imp1:
                    imp2.append(det)
                imp1.append(det)
                logger.info("{} implicates {} from {}".format(neighbor, det, idx))

    infatvs = df_meta.loc[imp2, 'FATV IN']
    outfatvs = df_meta.loc[imp2, 'FATV OUT']

    invals = df_cfatv.loc[infatvs, 'ERR'].values
    outvals = df_cfatv.loc[outfatvs, 'ERR'].values

    miscount = (outvals - invals)
    return imp2, miscount
