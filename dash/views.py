from dash import app
from dash.models import *

from flask import render_template, redirect, url_for, request, jsonify
from sqlalchemy import func

import numpy as np
import pandas as pd
import os, datetime
from operator import attrgetter

from pems.download import PemsDownloader as PDR
from dash.scripts.balance import diagnose
from dash.scripts.utils import revise_meta

@app.route('/')
def index():
	date = request.args.get('date')
	
	if not date:
		date = db.session.query(func.max(Log.date)).scalar()
		return redirect(url_for('index', date = "{0:%Y}-{0:%m}-{0:%d}".format(date) ))

	date = datetime.datetime.strptime(date, '%Y-%m-%d')
	return render_template('layouts/index.html', date = date.date())

@app.route('/update', methods = ['PATCH'])
def analyze():

	command = request.get_json()
	pdr = PDR()

	one_day = datetime.timedelta(days = 1)
	zero_time = datetime.time(0, 0)
	to_datetime = lambda day: datetime.datetime.combine(day, zero_time)
	
	for date in command["dates"]:
		date = datetime.datetime.strptime(date, '%Y-%m-%d').date() if date else None
		time = datetime.datetime.now()

		if Log.query.filter_by(date = date).order_by(Log.time.desc()).first():
			continue

		day, df_meta = pdr.download('meta')
		df_meta = revise_meta(df_meta)

		day, df_day = pdr.download('station_5min', date = date, parse_dates = True)
		fatvs = FATV.query.all()
		df_cfatv = pd.DataFrame({
				'IN':  [[d.id for d in fatv.detectors_in ] for fatv in fatvs],
				'OUT': [[d.id for d in fatv.detectors_out] for fatv in fatvs]
			}) # Just reconstruct df_cfatv, its easier

		# Include FATV data in df_meta
		df_meta['FATV IN'] = None
		df_meta['FATV OUT'] = None
		for fid, fatv in df_cfatv.iterrows():
			df_meta.loc[df_meta.index & fatv['IN'], 'FATV IN'] = fid
			df_meta.loc[df_meta.index & fatv['OUT'], 'FATV OUT'] = fid

		Log.query.filter(Log.date == to_datetime(day)).delete()
		data.query.filter(data.timestamp >= to_datetime(day)).filter(data.timestamp < to_datetime(day + one_day)).delete()
		db.session.commit()

		# Curate data to efficiently insert from pandas
		df_day.drop(['District', 'Freeway', 'Direction', 'Lane Type', 'Station Length'], axis = 1, inplace = True)
		df_day.to_sql('data', con = db.engine, index = False, if_exists = 'append')

		# Perform network diagnosis
		imp2, miscount = diagnose(df_meta, df_day, df_cfatv)
		df_diag = pd.DataFrame({
			'DET_ID': imp2,
			'Date': date,
			'Miscount': miscount,
			'Comment': ['' for idx in imp2]
		})

		diag_types = {c.name : c.type for c in Diagnosis.__table__.columns} # Is this necesary?
		df_diag.to_sql('diagnosis', con = db.engine, dtype = diag_types, index = False, if_exists = 'append')

		log = Log(date = day, time = time)
		db.session.add(log)
		db.session.commit()

	return jsonify({'Success': True}), 200, {'Content-Type': 'application/json'}

@app.route('/detectors/all')
def detectors():
	dets = Detector.query.all()
	data = {
		d.id: {
			'loc': [d.lat, d.lon],
			# 'error': error,
			'fatv_in': d.fatv_in_id,
			'fatv_out': d.fatv_out_id,
		} for d in dets}
	return jsonify(data)

@app.route('/detector/<int:det_id>')
def detector(det_id):
	det = Detector.query.get(det_id)
	return render_template('description.html', detector = det)

@app.route('/detectors/fatv/<int:fatv_id>')
def fatv(fatv_id):
	fatv = FATV.query.get(fatv_id)
	return jsonify([d.id for d in fatv.detectors])

@app.route('/errors')
def diagnoses():
	date = datetime.datetime.strptime(request.args.get('date'), '%Y-%m-%d')
	diagnoses = Diagnosis.query.filter(Diagnosis.date == date)
	return jsonify([dg.detector_id for dg in diagnoses])

@app.route('/errors', methods = ['POST'])
def errors():
	data = request.get_json()
	diagnoses = [Diagnosis(datum) for datum in data["diagnoses"]]
	db.session.add_all(diagnoses)
	db.session.commit()
	# diag_date = datetime.datetime.strptime(data['date'], '%Y-%m-%d').date()
	# diag = Diagnosis(data['det'], diag_date, data['miscount'], data['comment'])
	# db.session.add(diag)
	# db.session.commit()
	app.logger.info(data)
	return jsonify(data), 200, {'ContentType':'application/json'}

@app.route('/fatvs')
def fatvs():
	fatvs = FATV.query.all()
	data = {
		fatv.id: {
			'IN': [det.id for det in fatv.detectors_in],
			'OUT': [det.id for det in fatv.detectors_out]
		} for fatv in fatvs
	}
	return jsonify(data)

@app.route('/fatv/<int:fatv_id>/flows')
def fatv_data(fatv_id):
	fatv = FATV.query.get(fatv_id)
	fin = fatv.detectors_in
	fout = fatv.detectors_out

	date = request.args.get('date')
	start = datetime.datetime.strptime(date, '%Y-%m-%d')
	end = start + datetime.timedelta(days = 1)

	fdin = [
		d.data.order_by('timestamp')\
			.filter(data.timestamp >= start)\
			.filter(data.timestamp <  end)\
			.with_entities('timestamp', 'flow')\
			.all()
		for d in fin
	]

	fdout = [
		d.data.order_by('timestamp')\
			.filter(data.timestamp >= start)\
			.filter(data.timestamp <  end)\
			.with_entities('timestamp', 'flow')\
			.all()
		for d in fout
	]

	arr_in = np.array([zip(*d)[1] for d in fdin], dtype = np.float)
	arr_out = np.array([zip(*d)[1] for d in fdout], dtype = np.float)
	try:
		x = zip(*fdin[0])[0]
	except IndexError as e:
		print fdin
		raise

	plot = {
		'IN': {
			'detectors': [d.id for d in fin],
			'data': {
				'x': x,
				'y': [n if not np.isnan(n) else None for n in np.sum(arr_in, axis = 0)],
				'mode': 'lines',
				'name': 'IN'
			}
		},

		'OUT': {
			'detectors': [d.id for d in fout],
			'data': {
				'x': x,
				'y': [n if not np.isnan(n) else None for n in np.sum(arr_out, axis = 0)],
				'mode': 'lines',
				'name': 'OUT'
			}
		}
	}

	return jsonify(plot)

@app.route('/neighborhood/<int:det_id>')
def neighborhood(det_id):
	det = Detector.query.get(det_id)
	fin, fout = det.fatv_in, det.fatv_out
	dets = set((fin.detectors if fin else []) + (fout.detectors if fout else []))
	return jsonify([d.id for d in dets])
