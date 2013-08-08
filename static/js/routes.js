App.Router = Backbone.Router.extend({
    routes : {
        "date/:date" : "viewDate",
        "uid/:uid" : "viewUid",
        ":id" : "ViewLog",
        "" : "viewSummary"
    },
    initialize : function(options) {
        this.listenTo(App.eventsFilter, 'add remove change', this.updateUrl);
        this.eventsListView = new App.EventsListView({
            collection : App.eventLogs
        });
        this.logTotalsView = new App.LogTotalsView({
            collection : App.eventLogs.fullCollection,
            template : '#summary-panel-template',
            el : '#summary'
        });
    },
    updateUrl : function() {'use strict';
        var url='';
        var selectedDate = App.eventsFilter.get('date');
        var selectedUid = App.eventsFilter.get('uid');
        if (selectedUid) {
            url='uid/' + selectedUid;
        }
        else if (selectedDate) {
            url='date/' + selectedDate.format('YYYY-MM-DD');
        }
        this.navigate(url);
    },
   /* viewFilteredList : function(query) {'use strict';
        var items = query.split('&');
        var selectedDate = null, selectedUid = null;
        items.forEach(function(item) {
            var params = item.split('=');
            if (params.length == 2) {
                if (params[0] == 'date') {
                    selectedDate = moment(params[1]);
                } else if (params[0] == 'uid') {
                    selectedUid = params[1];
                }
            }
        });
        App.eventsFilter.set({
            'date' : selectedDate,
            'uid' : selectedUid
        });
    }, */
    viewLog : function(model) {'use strict';
        var id;
        if ( typeof (model) == 'string') {
            id = model;
            model = App.eventLogs.fullCollection.get(id);
        } else {
            id = model.id;
        }

        if (id!==undefined && model!==undefined) {
            this.navigate('id/' + id);
            this.eventsListView.$el.hide();
            if (this.eventDetailView) {
                this.eventDetailView.remove();
            }
            this.eventDetailView = new App.EventDetailView({
                model : model
            });
            $('#logging').append(this.eventDetailView.el);
            this.eventDetailView.render();
        }
    },
    viewSummary : function() {'use strict';
        if (this.eventDetailView) {
            this.eventDetailView.remove();
            this.eventDetailView = null;
            this.updateUrl();
        }
        this.eventsListView.$el.show();
        App.eventsFilter.clear();
        //this.navigate('/');
        //App.eventLogs.trigger('filter');
    },
    viewDate: function(date){
        'use strict';
        if(typeof(date)=='string'){
            date = moment(date);
        }
        App.eventsFilter.setDate(date);
        //App.eventLogs.trigger('filter');
    },
    viewUid: function(uid){
        'use strict';
        App.eventsFilter.setUid(uid);
        //this.updateUrl();
        //App.eventLogs.trigger('filter');
    }
});

