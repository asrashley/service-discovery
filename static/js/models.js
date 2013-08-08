window.App = window.App || {};
/*
 App.Event = DS.Model.extend({
 EVENT_TYPES:['start','zeroconf','upnp','cloud','end'],
 ev: DS.attr('string'),
 ts: DS.attr('date'),
 log: DS.belongsTo('App.EventLog')
 });
 */
App.Event  = Backbone.Model.extend({
    EVENT_TYPES:['start','zeroconf','upnp','cloud','end'],
    defaults: {
        ev: 'start',
        ts: new moment()
    }
});

App.EventLog = Backbone.Model.extend({
    defaults : {
        client : false,
        extra : {},
        date : new Date(),
        entries : []
    },
    parse : function(response) {
        'use strict';
        var self=this;
        if(typeof(response.date)=='string'){
            response.date = moment(response.date);
        }
        response.entries = response.entries.map(function(item,index){
           return new App.Event({ev:item.ev, ts:moment(item.ts), id:response.id+index});
        });
        return response;
    },
    comparator : function(log) {
        return log.get('date');
    },
    count : function(event, filter) {'use strict';
        var events, entry, rv = 0;
        events = this.get('entries');
        return events.filter(function(item) {
        	var rv = (item.ev || item.get('ev')) == event;
        	if(rv && filter){
        		rv = filter(item);
        	}
        	return rv;
        }).length;
    },
    /* returns list of times taken for each of the given discovery method */
    durations : function(event, filter) {'use strict';
        var events, start = null, times = [];
        events = this.get('entries');
    	if(filter){
    		events = _.filter(events,filter);
    	}
        events.forEach(function(entry) {
            var ts, ev = entry.get('ev');
            if (ev == 'start') {
                start = entry.get('ts');
            } else if (ev == event && start !== null) {
                ts = entry.get('ts');
                times.push(ts.diff(start));
                //times.push(entry.get('ts').getTime() - start);
                start = null;
            }
        });
        return times;
    },
    /* calculates the average time taken for each of the given discovery method */
    duration : function(event, filter) {
        var avg, times = this.durations(event, filter);
        if (times.length > 0) {
            avg = 0;
            times.forEach(function(t) {
                avg += t;
            });
            avg = Math.round(avg / times.length) / 1000.0;
            return avg
        }
        return 'N/A';
    },
    totalCount : function() {
        return this.count('start');
    },
    cloudCount : function() {
        return this.count('cloud');
    },
    zeroconfCount : function() {
        return this.count('zeroconf');
    },
    upnpCount : function() {
        return this.count('upnp');
    },
    cloudDuration : function() {
        return this.duration('cloud');
    },
    upnpDuration : function() {
        return this.duration('upnp');
    },
    zeroconfDuration : function() {
        return this.duration('zeroconf');
    },
    description: function(){
    	var rv=[], name = this.get('name');
    	if(name){
    		rv.push(name);
    	}
    	rv.push(this.get('uid'));
    	return rv.join('\n');
    }
    /*    uid: DS.attr('string'),
     date: DS.attr('date'),
     isoDate: function(){
     return this.get('date').toISOString();
     }.property('date'),
     client: DS.attr('boolean'),
     name: DS.attr('string'),
     loc: DS.attr('geoPt'),
     city: DS.attr('string'),
     addr: DS.attr('string'),
     extra: DS.attr('jsonProperty'),
     events: DS.hasMany('App.Event'),*/
});

App.EventLogCollection = Backbone.PageableCollection.extend({
    model : App.EventLog,
    url : '/logs/event_logs',
    mode: "infinite",
    state: {
    	firstPage: 1,
        pageSize: 15,
        sortKey: "date",
        order: 1
    },
    queryParams:{
    	currentPage: null
    },
    /*parse : function(response) {
        'use strict';
        if('meta' in response){
            this.meta = response.meta;
            delete response.meta;
        }
        if('event_logs' in response){
            response = response.event_logs;
        }
        return response;
    },
    comparator : function(item) {
        'use strict';
        return item.get('date');
    },*/
});
App.eventLogs = new App.EventLogCollection();

App.EventsFilterModel = Backbone.Model.extend({
	defaults:{
		date: null,
		uid: null
	},
	setDate: function(date){
		'use strict';
		if(typeof(date)=='string'){
			date = moment(date);
		}
		this.set({date:date, uid:null});
		//App.eventLogs.trigger('filter');
	},
	setUid: function(uid){
		'use strict';
		this.set({uid:uid, date:null});
		//this.updateUrl();
		//App.eventLogs.trigger('filter');
	},
	clear: function(){
		this.set({uid:null, date:null});
		//this.updateUrl();
		//App.eventLogs.trigger('filter');	  
	},
	isEmpty: function(){
		return this.attributes.date===null && this.attributes.uid===null;
	},
	itemFilter: function(model){
		if(this.attributes.uid!==null){
			return model.attributes.uid==this.attributes.uid;
		}
		if(this.attributes.date!==null){
			return model.attributes.date.year()==this.attributes.date.year() &&
				model.attributes.date.month()==this.attributes.date.month() &&
				model.attributes.date.day()==this.attributes.date.day();
		}
		return true;
    },
	
});
App.eventsFilter = new App.EventsFilterModel();
