var Selector = {
	'settings': {
		'home': [34.146752, -118.029146],
		'homeZoom': 12
	},

	'errorIcon': L.icon({
		iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
		shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',

		iconSize: [25, 41],
		iconAnchor: [12, 41],
		popupAnchor: [1, -34],
		shadowSize: [41, 41],
		shadowAnchor: [12, 41]  // the same for the shadow
	}),

	'standardIcon': L.icon({
		iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
		shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',

		iconSize: [25, 41],
		iconAnchor: [12, 41],
		popupAnchor: [1, -34],
		shadowSize: [41, 41],
		shadowAnchor: [12, 41]  // the same for the shadow
	}),

	'inIcon': L.icon({
		iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
		shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',

		iconSize: [25, 41],
		iconAnchor: [12, 41],
		popupAnchor: [1, -34],
		shadowSize: [41, 41],
		shadowAnchor: [12, 41]  // the same for the shadow
	}),

	'outIcon': L.icon({
		iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-orange.png',
		shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',

		iconSize: [25, 41],
		iconAnchor: [12, 41],
		popupAnchor: [1, -34],
		shadowSize: [41, 41],
		shadowAnchor: [12, 41]  // the same for the shadow
	}),

	'selectedMarker': L.circleMarker([null, null], {
		color: '#5577aa',
		opacity: 0.8,
		radius: 10
	}),

	'createMarkers': function() {
		this.detectors = {};
		var self = this;
		var target = root_api + 'data/detectors/latest'
		$.getJSON(target, function(json) {
			$.each(json, function(id, info) {
				var loc = [info.Latitude, info.Longitude]
				var marker = L.marker(info.loc, {
					icon: self.standardIcon,
					opacity: 0.9
				});
				marker.id = id;
				marker.info = info;

				marker.bindPopup(marker.id);
				marker.on({
					'click': function(e) {self.onSelect(this)},
					'mouseover': self.onHover,
					'mouseout': self.onExit,
				});

				self.detectors[id] = marker;
			});

			self.markErrors(date);
			self.all_layer = L.featureGroup($.map(self.detectors, function(det) {return det;}));
			self.all_layer.addTo(self.map);
		});
	},

	'markErrors': function(date) {
		for (id in this.marked) {
			this.detectors[id].setIcon(this.standardIcon);
		};
		var self = this;
		$.getJSON('errors?date=' + date, function(marked) {
			self.marked = marked;
			$.each(marked, function(idx, id) {
				self.detectors[id].setIcon(self.errorIcon);
			});
		});
	},

	'onSelect': function(detector) {
		var old = this.selected;

		this.selectedMarker.setLatLng(detector.info.loc);
		if (!old) {
			this.selectedMarker.addTo(this.map);
		};

		this.selected = detector;
		this.describe(detector);
		this.showPlots(detector, old);
		this.showNeighborhood(detector)
	},

	'onHover': function(e) {
		this.openPopup();
	},

	'onExit': function(e) {
		this.closePopup();
	},

	'getFATVs': function() {
		var self = this;
		this.fatvs = {};
		$.getJSON('fatvs', function(json) {
			$.each(json, function(fid, ids) {
				self.fatvs[fid] = $.map(ids['IN'].concat(ids['OUT']), function(id) {
					return self.detectors[id];
				});
			});
		});
	},

	'init': function() {
		this.map = L.map('leaf-map').setView(this.settings.home, this.settings.homeZoom);
		this.n_layer = null;
		this.selected = null;
		this.marked = {};

		L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token={accessToken}', {
			attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://mapbox.com">Mapbox</a>',
			maxZoom: 18,
			id: 'mapbox.streets',
			accessToken: 'pk.eyJ1IjoicnBpZ290dCIsImEiOiJjajR5b2gza3QxeG9sMndyNDI1ZWx1dnRoIn0.KWaGwMzYy_P5PRjGJY5xXQ'
		}).addTo(this.map);

		this.createMarkers();
		this.getFATVs();

		this.resetButton = L.easyButton('fa-home fa-lg', this.resetView.bind(this));
		this.resetButton.addTo(this.map);

		var self = this;
		this.showHideButton = L.easyButton({
		    states: [{
		            stateName: 'hide',
		            icon:      'fa-eye fa-lg',
		            title:     'Show only selected neighborhood',
		            onClick: function(btn, map) {
		            	if (!!self.n_layer) {
		            		self.map.removeLayer(self.all_layer);
		            		self.n_layer.addTo(self.map);
			                btn.state('show');
		            	};
		            }
		        }, {
		            stateName: 'show',
		            icon:      'fa-eye-slash fa-lg',
		            title:     'Show all detectors',
		            onClick: function(btn, map) {
		            	self.map.removeLayer(self.n_layer);
		            	self.all_layer.addTo(self.map);
		                btn.state('hide');
		            }
		    }]
		});
		this.showHideButton.addTo(this.map);

		return this;
	},

	'resetView': function(btn, map) {
		map.fitBounds(this.all_layer.getBounds());
	},

	'describe': function(detector) {
		var div = $('#detector-info');
		$.ajax({
			'url': '/detector/' + detector.id,
			'success': function(data, status, jqxhr) {
				div.html(data);
			}
		});
	},

	'showPlots': function(detector, old) {
		var self = this;

		function titleize(dets) {
			return $.map(dets, function(det) {
				if (self.selected.id == det) {
					return $('<a>', {
						text: det,
						href: '#'
					})[0].outerHTML;
				} else {
					return det
				}
			});
		}

		if (detector.info.fatv_in) {
			$.getJSON('/fatv/' + detector.info.fatv_in + '/flows?date=' + date, function(flows) {
				// Plotly.purge('plot-1');
				if (self.selected == detector) {
					Plotly.newPlot('plot-1', [flows['IN']['data'], flows['OUT']['data']], {
						'title': 'FATV ' + detector.info.fatv_in + '<br>' +
						'IN: ' + titleize(flows['IN']['detectors']).join(', ') + '<br>' +
						'OUT: ' + titleize(flows['OUT']['detectors']).join(', '),

						'xaxis': {
							'title': 'Time'
						},
						'yaxis': {
							'title': 'Vehicles / 5min'
						}
					});
				};
			});
		} else {
			Plotly.purge('plot-1');
		};

		if (detector.info.fatv_out) {
			$.getJSON('/fatv/' + detector.info.fatv_out + '/flows?date=' + date, function(flows) {
				// Plotly.purge('plot-2');
				if (self.selected == detector) {
					Plotly.newPlot('plot-2', [flows['IN']['data'], flows['OUT']['data']], {
						'title': 'FATV ' + detector.info.fatv_out + '<br>' +
						'IN: ' + titleize(flows['IN']['detectors']).join(', ') + '<br>' +
						'OUT: ' + titleize(flows['OUT']['detectors']).join(', '),
						
						'xaxis': {
							'title': 'Time'
						},
						'yaxis': {
							'title': 'Vehicles / 5min'
						}
					});
				};
			});
		} else {
			Plotly.purge('plot-2')
		};
	},

	'showNeighborhood': function(detector) {
		var dets = [detector];
		var din = this.fatvs[detector.info.fatv_in];
		var dout = this.fatvs[detector.info.fatv_out];

		if (din) {
			dets = dets.concat(din);
		}
		if (dout) {
			dets = dets.concat(dout);
		}

		if (this.n_layer) {
			this.map.removeLayer(this.n_layer);
		}

		this.n_layer = L.featureGroup(dets);
		this.map.removeLayer(this.all_layer);
		this.n_layer.addTo(this.map);
		this.map.fitBounds(this.n_layer.getBounds());
		this.showHideButton.state('show');
	}
};

(function($) {
var re = /([^&=]+)=?([^&]*)/g;
var decodeRE = /\+/g;  // Regex for replacing addition symbol with a space
var decode = function (str) {return decodeURIComponent( str.replace(decodeRE, " ") );};
$.parseParams = function(query) {
    var params = {}, e;
    while ( e = re.exec(query) ) { 
        var k = decode( e[1] ), v = decode( e[2] );
        if (k.substring(k.length - 2) === '[]') {
            k = k.substring(0, k.length - 2);
            (params[k] || (params[k] = [])).push(v);
        }
        else params[k] = v;
    }
    return params;
};
})(jQuery);

$('document').ready(function() {
	root_api = 'https://k30xor61gh.execute-api.us-west-2.amazonaws.com/alpha/'
	date = $.parseParams(window.location.search.substr(1)) || ''
	selector = Selector.init();

	$('#plot-1').on('plotly_relayout', function(e, edata) {
        Plotly.relayout('plot-2', edata);
    });

    $('#datepicker').datepicker({
    	maxDate: 0
    });
});
