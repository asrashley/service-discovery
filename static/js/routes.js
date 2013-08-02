App.Router = Backbone.Router.extend({
  routes: {
    "q/:query": "viewFilteredList",
    ":id": "ViewLog",
    "/":"viewSummary"
    // ... other routes
  },
  _generateUrl : function(){
	  'use strict';
	  var q = [];
	  if(App.selectedDate){
		  q.push('date='+App.selectedDate.format('YYYY-MM-DD'));
	  }
	  if(App.selectedUid){
		  q.push('uid='+App.selectedUid);
	  }
	  return 'q/'+q.join('&');
  },
  setDateFilter: function(date){
	  'use strict';
	  if(typeof(date)=='string'){
		  date = moment(date);
	  }
	  App.selectedDate = date;
	  this.navigate(this._generateUrl());
	  App.eventLogs.trigger('filter');
  },
  clearDateFilter: function(){
	  delete App.selectedDate;
	  this.navigate(this._generateUrl());
	  App.eventLogs.trigger('filter');	  
  },
  setUidFilter: function(uid){
	  'use strict';
	  App.selectedUid = uid;
	  this.navigate(this._generateUrl());
	  App.eventLogs.trigger('filter');
  },
  clearUidFilter: function(){
	  delete App.selectedUid;
	  this.navigate(this._generateUrl());
	  App.eventLogs.trigger('filter');	  
  },
  viewFilteredList: function(query){
	  'use strict';
	  var items = query.split('&');
	  delete App.selectedUid;
	  delete App.selectedDate;
	  items.forEach(function(item){
		 var params = item.split('=');
		 if(params.length==2){
			 if(params[0]=='date'){
				 App.selectedDate = moment(params[1]);		 
			 }
			 else if(params[0]=='uid'){
				 App.selectedUid = params[1];		 
			 }
		 }
	  });
	  App.eventLogs.trigger('filter');
  },
  viewLog: function(id) {
	  'use strict';
    console.log("View single log opened.");
  },
  viewSummary: function(){
	  'use strict';
	  delete App.selectedDate;
	  this.navigate('/');
	  App.eventLogs.trigger('filter');
  }
});

App.appRouter = new App.Router();

Backbone.history.start();
