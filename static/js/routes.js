App.Router = Backbone.Router.extend({
  routes: {
    "q/:query": "viewFilteredList",
    "uid/:id": "ViewLog",
    "":"viewSummary"
    // ... other routes
  },
  initialize: function(options){
	  this.listenTo(App.eventsFilter,'add remove change', this.updateUrl);
	  this.eventsListView = new App.EventsListView({
		  collection : App.eventLogs
	  });
	  this.logTotalsView = new App.LogTotalsView({
		  collection : App.eventLogs.fullCollection,
		  template:'#summary-panel-template',
		  el:'#summary'
	  });
  },
  updateUrl : function(){
	  'use strict';
	  var q = [];
	  var selectedDate = App.eventsFilter.get('date');
	  var selectedUid = App.eventsFilter.get('uid');
	  if(selectedDate){
		  q.push('date='+selectedDate.format('YYYY-MM-DD'));
	  }
	  if(selectedUid){
		  q.push('uid='+selectedUid);
	  }
	  if(App.eventLogs.state.currentPage){
		  q.push('page='+App.eventLogs.state.currentPage);		  
	  }
	  if(q.length){
		  this.navigate('q/'+q.join('&'));
	  }
	  else{
		  this.navigate('');
	  }
  },
  viewFilteredList: function(query){
	  'use strict';
	  var items = query.split('&');
	  var selectedDate = null, selectedUid=null; 
	  items.forEach(function(item){
		 var params = item.split('=');
		 if(params.length==2){
			 if(params[0]=='date'){
				 selectedDate = moment(params[1]);		 
			 }
			 else if(params[0]=='uid'){
				 selectedUid = params[1];		 
			 }
		 }
	  });
	  App.eventsFilter.set({'date':selectedDate,'uid':selectedUid});
	  //App.eventLogs.trigger('filter');
  },
  viewLog: function(model) {
	  'use strict';
	  var id;
	  if(typeof(model)=='string'){
		  id = model;
		  model = App.eventLogs.fullCollection.get(id);
	  }
	  else{
		  id = model.id;
	  }
	  this.navigate('uid/'+id);
	  this.eventsListView.$el.hide();
	  if(this.eventDetailView){
		  this.eventDetailView.remove();
	  }
	  this.eventDetailView = new App.EventDetailView({model:model});
	  $('#logging').append(this.eventDetailView.el);
	  this.eventDetailView.render();
  },
  viewSummary: function(){
	  'use strict';
	  if(this.eventDetailView){
		  this.eventDetailView.remove();
		  this.eventDetailView=null;
	  }
	  this.eventsListView.$el.show();
	  App.eventsFilter.clearUidFilter();
	  App.eventsFilter.clearDateFilter();
	  this.updateUrl();
	  //this.navigate('/');
	  //App.eventLogs.trigger('filter');
  }
});

