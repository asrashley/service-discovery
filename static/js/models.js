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

App.Event = DS.Model.extend({
    EVENT_TYPES:['start','zeroconf','upnp','cloud','end'],
    ev: DS.attr('string'),
    ts: DS.attr('date'),
    log: DS.belongsTo('App.EventLog')
});

App.EventLog = DS.Model.extend({
    uid: DS.attr('string'),
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
    events: DS.hasMany('App.Event'),
});
