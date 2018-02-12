from dash import db

class Log(db.Model):
	__tablename__ = 'logs'
	id = db.Column('id', db.Integer, primary_key = True)
	date = db.Column('Date', db.DateTime, unique = True)

class Detector(db.Model):
	__tablename__ = 'detectors'
	id = db.Column('ID', db.Integer, primary_key = True)
	fwy = db.Column('Fwy', db.Integer)
	dir = db.Column('Dir', db.String(1))
	name = db.Column('Name', db.String(40))
	# city = db.Column('City', db.String(40))
	county = db.Column('County', db.String(40))
	ltype = db.Column('Type', db.String(25))
	lanes = db.Column('Lanes', db.Integer)
	length = db.Column('Length', db.Float)
	msid = db.Column('MS ID', db.Integer)
	abspm = db.Column('Abs PM', db.Float)
	capm = db.Column('CA PM', db.String(10))
	lat = db.Column('Latitude', db.Float)
	lon = db.Column('Longitude', db.Float)
	exact = db.Column('Exact', db.Boolean)
	fatv_in_id = db.Column('FATV IN', db.Integer, db.ForeignKey('FATV.id'))
	fatv_out_id = db.Column('FATV OUT', db.Integer, db.ForeignKey('FATV.id'))
	data = db.relationship('data', backref = 'detector', lazy = 'dynamic')

	def __repr__(self):
		return "Detector <{}>".format(self.id)

class FATV(db.Model):
	id = db.Column(db.Integer, primary_key = True)
	detectors_in = db.relationship('Detector', backref = 'fatv_in', foreign_keys = 'Detector.fatv_in_id')
	detectors_out = db.relationship('Detector', backref = 'fatv_out', foreign_keys = 'Detector.fatv_out_id')

	def __init__(self, id):
		self.id = id

	def __repr__(self):
		return "FATV <{}>".format(self.id)

	@property
	def detectors(self):
		return self.detectors_in + self.detectors_out

class Diagnosis(db.Model):
	index = db.Column(db.Integer, primary_key = True)
	detector_id = db.Column('DET_ID', db.Integer)
	date = db.Column('Date', db.DateTime)
	miscount = db.Column('Miscount', db.Integer)
	comment = db.Column('Comment', db.String(140))

	def __init__(self, detector_id, date, miscount, comment):
		self.detector_id = detector_id
		self.date = date
		self.miscount = miscount
		self.comment = comment

	def __repr__(self):
		return "Diagnosis <{}> <{}>".format(self.index, self.date)

class data(db.Model):
	id = db.Column('Index', db.Integer, primary_key = True)
	timestamp = db.Column('Timestamp', db.DateTime)
	detector_id = db.Column('Station', db.ForeignKey(Detector.id))
	samples = db.Column('Samples', db.Integer)
	observed = db.Column('Observed', db.Integer)
	flow = db.Column('Flow', db.Float)
	occupancy = db.Column('Occupancy', db.Float)
	speed = db.Column('Speed', db.Float)

	def __repr__(self):
		return "Data <{}> {}: {}".format(self.detector_id, self.timestamp, self.flow)