
Handlebars.registerHelper('dateFormat', function(context, block) {
  if (window.moment) {
    var f = block.hash.format || "MMM Do, YYYY";
    return moment(Date(context)).format(f);
  }else{
    return context;   //  moment plugin not available. return data as is.
  };
});

/* HELPER: #key_value
 *
 * Usage: {{#key_value obj}} Key: {{key}} // Value: {{value}} {{/key_value}}
 *
 * Iterate over an object, setting 'key' and 'value' for each property in
 * the object. */
Handlebars.registerHelper("key_value", function(obj, block) {
    var buffer = [],
        key;
    if(typeof(obj)=='string'){
        obj = this.get(obj);
    }
    for (key in obj) {
        if (obj.hasOwnProperty(key)) {
            buffer.push(block.fn({key: key, value: obj[key]}));
        }
    }

    return buffer.join('');
});
Handlebars.registerHelper("each_with_key", function(obj, block) {
    var context,
        buffer = [],
        key,
        keyName = fn.hash.key;

    for (key in obj) {
        if (obj.hasOwnProperty(key)) {
            context = obj[key];

            if (keyName) {
                context[keyName] = key;
            }

            buffer.push(block.fn(context));
        }
    }

    return buffer.join('');
});


App.LogController = Ember.ObjectController.extend({
    count: function(event){
        'use strict';
        var events, entry, rv=0;
        events = this.get('model.events');
        return events.filterProperty('ev', event).get('length');
    },
    duration: function(event) { /* calculates the average time taken for each of the given discovery method */
        'use strict';
        var events, start=null, times=[], avg;
        events = this.get('model.events');
        events.forEach(function(entry){
            if(entry.get('ev')=='start'){
                start = entry.get('ts').getTime()
            }
            else if(entry.get('ev')==event && start!==null){
                times.push(entry.get('ts').getTime() - start);
                start = null;
            }
        });
        if(times.length>0){
            avg=0;
            times.forEach(function(t){
                avg += t;
            });
            avg = Math.round(avg/times.length)/1000.0;
            return avg
        }
        return 'N/A';
    },
    totalCount: function(){
        return this.count('start');
    }.property('model.events.@each.ev'),
    cloudCount: function(){
        return this.count('cloud');
    }.property('model.events.@each.ev'),
    zeroconfCount: function(){
        return this.count('zeroconf');
    }.property('model.events.@each.ev'),
    upnpCount: function(){
        return this.count('upnp');
    }.property('model.events.@each.ev'),
    cloudDuration: function(){
        return this.duration('cloud');
    }.property('model.events.@each.ev','model.events.@each.ts'),
    upnpDuration: function(){
        return this.duration('upnp');
    }.property('model.events.@each.ev','model.events.@each.ts'),
    zeroconfDuration: function(){
        return this.duration('zeroconf');
    }.property('model.events.@each.ev','model.events.@each.ts')
});

App.LogsController = Ember.ArrayController.extend({
    itemController : 'log',
    sumCounts : function(field) {
        var rv = 0, logs = this.filter();
        logs.forEach(function(log) {
            rv += log.get(field);
        });
        return rv;
    },
    sumTotalCounts : function() {
        return this.sumCounts('totalCount');
    }.property('@each.totalCount')
});
