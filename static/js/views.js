/*  **AppView** is the top-level piece of UI. */
App.AppView = Backbone.View.extend({

    // Instead of generating a new element, bind to the existing skeleton of
    // the App already present in the HTML.
    el : '#logging',

    // Our template for the line of statistics at the bottom of the app.
    statsTemplate : _.template($('#event-foot').html()),
    events: {
    	'click th.uid': 'clearUidFilter',
    	'click th.date': 'clearDateFilter'
    },
    // At initialization we bind to the relevant events on the `Todos`
    // collection, when items are added or changed.
    initialize : function() {
        this.$header = this.$('thead');
        this.$footer = this.$('tfoot');

        this.listenTo(App.eventLogs, 'add', this.addOne);
        this.listenTo(App.eventLogs, 'reset', this.addAll);
        this.listenTo(App.eventLogs, 'all', this.render);
        //this.on('selectDate', this.addAll);
        this.listenTo(App.eventLogs,'filter', this.addAll);

        App.eventLogs.fetch();
    },
    _itemFilter: function(item){
    	return (App.selectedDate===undefined || App.selectedDate.isSame(item.get('date'))) &&
    		(App.selectedUid==undefined || App.selectedUid==item.get('uid'));	
    },
    render : function() {'use strict';
        var self=this, context = {};
        if (App.eventLogs.length) {
        	this.$('.loading').hide();
        	this.$el.removeClass('loading');
            this.$header.show();
            this.$footer.show();
            context.totalCount = App.eventLogs.count('start', this._itemFilter);
            ['cloud', 'upnp', 'zeroconf'].forEach(function(name) {
                context[name + 'Count'] = App.eventLogs.count(name, self._itemFilter);
                context[name + 'Duration'] = App.eventLogs.duration(name, self._itemFilter);
            });
            this.$footer.html(this.statsTemplate(context));
        } else {
            this.$header.hide();
            this.$footer.hide();
        }
    },
    // Add a single EventLog item to the list by creating a view for it, and
    // appending its element
    addOne : function(item) {
    	if(this._itemFilter(item)){
    		var view = new App.EventView({
    			model : item
    		});
    		this.$('tbody').append(view.render().el);
    	}
        return this;
    },

    // Add all items in the **EventLogCollection** collection at once.
    addAll : function() {
    	'use strict';
    	//var self=this;
        this.$('tbody').empty();
        /*if(App.selectedDate){
            App.eventLogs.filter(function(item){
            	return App.selectedDate.isSame(item.get('date'));
            }).forEach(this.addOne, this);        	        	
        }
        else{*/
            App.eventLogs.each(this.addOne, this);        	
        //}
    },
    clearUidFilter: function(){
    	App.appRouter.clearUidFilter();
    },
    clearDateFilter: function(){
    	App.appRouter.clearDateFilter();
    }
    /*,selectDate : function(date){
    	if(typeof(date)=='string'){
    		date = moment(date);
    	}
    	this.selectedDate = date;
    	this.trigger('selectDate');
    }*/
});

/* The DOM element for an individual EventLog */
App.EventView = Backbone.View.extend({
    tagName : 'tr',

    // Cache the template function for a single item.
    template : _.template($('#event-row').html()),

    // The DOM events specific to an item.
    events : {
    	'click .uid': 'selectUid',
    	'click .date': 'selectDate'
        //'dblclick label': 'edit',
        //'keypress .edit': 'updateOnEnter',
        //'blur .edit': 'close'
    },

    /* The EventView listens for changes to its model, re-rendering. Since there's
     *  a one-to-one correspondence between an EventLog and an EventView a direct
     *  reference on the model can be used. */
    initialize : function() {'use strict';
        this.listenTo(this.model, 'change', this.render);
    },

    render : function() {'use strict';
        var self = this, attrs = this.model.toJSON();
        ['totalCount', 'cloudCount', 'zeroconfCount', 'upnpCount'].forEach(function(name) {
            attrs[name] = self.model[name].call(self.model);
        });
        attrs.model = this.model;
        this.$el.html(this.template(attrs));
        //this.$input = this.$('.edit');
        return this;
    },
    selectUid: function(ev){
    	'use strict';
    	App.appRouter.setUidFilter(this.model.get('uid'));
    },
    selectDate: function(ev){
    	'use strict';
    	App.appRouter.setDateFilter(this.model.get('date'));
    }
});

App.DateSelectButton = Backbone.View.extend({
    tagName : 'li',
    template : _.template('<%= date.format("DD MMMM YYYY") %>'),
    events : {
        'click' : 'selectDate'
    },
    initialize : function(options) {'use strict';
        //his.listenTo(this.model, 'change', this.render);
        this.key = this.options.key;
        this.$el.addClass('button');
        this.$el.attr('data-key',this.key);
        this.listenTo(App.eventLogs, 'filter', this.render);
    },
    render : function() {'use strict';
    	if(this.options.date.isSame(App.selectedDate)){
    		this.$el.addClass('active');
    	}        
    	else{
    		this.$el.removeClass('active');
    	}
        this.$el.html(this.template({
            date : this.options.date
        }));
        return this;
    },
    selectDate : function(ev) {
    	if(this.options.date.isSame(App.selectedDate)){
    		App.appRouter.clearDateFilter();
    	}
    	else{
            App.appRouter.setDateFilter(this.options.date);    		
    	}
    },
    order : function() {
        return this.options.date.valueOf();
    }
});

App.DateSelectView = Backbone.View.extend({
    el : '#datesel',
    // Cache the template function for a single item.
    initialize : function() {'use strict';
        this.$header = this.$('.header');
        this.$footer = this.$('.footer');
        this.dateList = [];
        this.listenTo(App.eventLogs, 'change', this.render);
        this.listenTo(App.eventLogs, 'add', this.addOne);
        this.listenTo(App.eventLogs, 'reset', this.addAll);
    },
    close : function() {
        this.stopListening();
    },
    addOne : function(log) {'use strict';
        var btn, exists, key, index, date = log.get('date');
        key = date.format('YYYYMMDD');
        exists = _.find(this.dateList,function(item){
        	return(item.key==key);
        });
        if(!exists){
        	btn = new App.DateSelectButton({
                date : date,
                key: key
            });
        	index = _.sortedIndex(this.dateList,btn,'key');
        	//console.log('index='+index);
        	if(index<this.dateList.length){
        		this.$('[data-key="'+this.dateList[index].key+'"]').before(btn.render().el);        		
        	}
        	else{
        		this.$('ul').append(btn.render().el);        		        		
        	}
        	this.dateList.splice(index,0,btn);
        }
    },
    addAll: function() {'use strict';
        var self = this;
        console.log('addAll');
        this.dateMap = {};
        App.eventLogs.forEach(function(item) {
            self.addOne(item, false);
        });
    },
    render : function() {'use strict';
        var self = this, dates;
        if (App.eventLogs.length) {
            this.$header.show();
            this.$footer.show();
        } else {
            this.$header.hide();
            this.$footer.hide();
        }
    }
});