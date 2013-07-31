
App.Router.map(function() {
  this.resource("logs", { path: '/' });
  this.resource("log", { path: "/:log_id" });
  this.resource("date", { path: "/date/:iso_date" });
});
App.LogsRoute = Ember.Route.extend({
  model: function() {
    return App.EventLog.find();
  },
  /*setupController: function(controller, items) {
    controller.set('model', items);
  },*/
  showPost: function (router, event) {
    var post = event.context;
    router.transitionTo('posts.show', post);
  }
});

App.LogRoute = Ember.Route.extend({
  model: function(params) {
    return App.EventLog.find(params.log_id);
  }
});
App.DateRoute = Ember.Route.extend({
  model: function(params) {
    return App.EventLog.find({date:params.iso_date});
  },
  serialize: function(model) {
    return { iso_date: model.date };
  }
});
