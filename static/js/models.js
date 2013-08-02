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
           return new App.Event({ev:item.ev, ts:moment(item.ts), id:self.id+index});
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
        	var rv = item.get('ev') == event;
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

App.EventLogCollection = Backbone.Collection.extend({
    model : App.EventLog,
    url : '/logs/event_logs',
    parse : function(response) {
        'use strict';
        if('meta' in response){
            this.meta = response.meta;
        }
        if('event_logs' in response){
            response = response.event_logs;
        }
        return response;
    },
    comparator : function(item) {
        'use strict';
        return item.get('date');
    },
    /**
     *  calculates the average time taken for each of the given discovery method
     * @param {string} event The name of the event type ("start", "upnp", "zeroconf", "cloud")
     */
    duration : function(event, filter) {
        'use strict';
        var avg, times = [];
        if(filter===undefined){
        	filter = function(){return true;};
        }
        this.filter(filter).forEach(function(item) {
            var t = item.durations(event);
            times.push.apply(times, t);
        });
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
    count : function(event,filter) {'use strict';
        'use strict';
        var rv = 0;
        if(filter===undefined){
        	filter = function(){return true;};
        }
        this.filter(filter).forEach(function(item) {
            rv += item.count(event);
        });
        return rv;
    }
});
App.eventLogs = new App.EventLogCollection();

/*
 window.App = Ember.Application.create({
 LOG_TRANSITIONS: true,
 LOG_VIEW_LOOKUPS: true,
 LOG_ACTIVE_GENERATION: true
 });
 App.Store = DS.Store.extend({
 revision: 13,
 adapter:'DS.RESTAdapter'
 });

 DS.RESTAdapter.registerTransform('geoPt', {
 serialize: function(value) {
 return {lat:value.get('lat'), lon:value.get('lon')};
 },
 deserialize: function(value) {
 return Ember.create({ lat: value.lat, lon: value.lon });
 }
 });

 DS.RESTAdapter.registerTransform('jsonProperty', {
 serialize: function(value) {
 return JSON.stringify(value);
 },
 deserialize: function(value) {
 if(value instanceof String){
 value = JSON.parse(value)
 }
 return value;
 }
 });

 */