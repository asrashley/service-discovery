(function() {
  var requestAnimationFrame = window.requestAnimationFrame || window.mozRequestAnimationFrame ||
                              window.webkitRequestAnimationFrame || window.msRequestAnimationFrame;
  if(requestAnimationFrame===undefined){
	  window.requestAnimationFrame = function(callback){
		  return setTimeout(callback,1000/60);
	  }
  }
  else if(!(requestAnimationFrame in window)){
	  window.requestAnimationFrame = requestAnimationFrame;
  }
})();



/*  **AppView** is the top-level piece of UI. */
App.EventsListView = Backbone.View.extend({
    el : '#EventsListView',
    events: {
    	'click th.devicetype': 'clearUidFilter',
    	'click th.date': 'clearDateFilter',
    	'click .next':'nextPage',
        'click .prev':'previousPage'
    },
    initialize : function() {
        this.$header = this.$('thead');
        this.$footer = this.$('tfoot');
        this.rows = new Backbone.Collection([],{model:App.EventView});
        this.footer = new App.LogTotalsView({collection:this.rows, template:'#event-foot-template', /*tagName:'tr' */ el:'#events tfoot'});
        this.footer.$el.addClass('logtotals');
        this.need_redraw=false;
        this.listenTo(this.collection, "add", this.insertRow);
        this.listenTo(this.collection, "remove", this.removeRow);
        this.listenTo(this.collection, "sort", this.refresh);
        this.listenTo(this.collection.fullCollection, "reset", this.refresh);
        this.listenTo(App.eventsFilter,'change', this.refresh);
        //this.listenTo(this.collection.fullCollection, "filter", this.refresh);
        //this.listenTo(this.collection.fullCollection, "add", this.addOne);
        //this.listenTo(this.collection, 'add', this.addOne);
        //this.listenTo(this.collection, 'reset', this.addAll);
        //this.listenTo(this.collection, 'all', this._requestRedraw);
        //this.on('selectDate', this.addAll);
        //this.listenTo(this.collection,'filter', this.addAll);
    },
    insertRow: function (model, collection, options) {
    	'use strict';
        var view, $el, $children, $rowEl, index;
    	if(!this._itemFilter(model)){
    		return this;
    	}
        if(collection===undefined || typeof(collection)=='number'){
        	collection = this.collection;
        }
        index = collection.indexOf(model);
        //console.log('Add '+model.cid+' '+index);
		view = new App.EventView({
			model : model
		});
		this.rows.add(view,{at:index});
        //this.rows.splice(index, 0, view);
        $el = this.$('tbody');
        $children = $el.children();
        $rowEl = view.render().$el;
        options = _.extend({render: true}, options || {});
        if (options.render) {
          if (index >= $children.length) {
            $el.append($rowEl);
          }
          else {
            $children.eq(index).before($rowEl);
          }
          this._requestRedraw();
        }
        return this;
    },
    removeRow: function (model, collection, options) {
    	'use strict';
    	var view;
    	if(options.index<this.rows.length && this.rows[options.index].model.id==model.id){
            console.log('Remove '+model.cid+' '+options.index);
            view = this.rows[options.index];
            this.rows.remove(view);
    		//view = this.rows.splice(options.index, 1);
    		//this.$('[data-cid="'+model.cid+'"]').remove();
    		//view[0].remove();
    		this._requestRedraw();
    	}
    },
    _requestRedraw : function(){
    	if(!this.need_redraw){
        	this.need_redraw=true;
        	requestAnimationFrame(this.render.bind(this));
    	}
    },
    _itemFilter: function(item){
    	var key, value;
    	for(key in App.eventsFilter.attributes){
    		value=App.eventsFilter.attributes[key];
    		if(value!==null){
    			if(value instanceof moment){
    				if(!value.isSame(item.get(key))){
    					return false;
    				}
    			}
    			else{
    				if(value!=item.get(key)){
    					return false;
    				}
    			}
    		}
    	}
    	return true;
    },
    render : function() {'use strict';
        var self=this, context = {};
        this.need_redraw=false;
        if (this.collection.length) {
            this.$header.show();
            this.$footer.show();
            if(this.collection.hasPrevious()){
            	this.$('.prev').show();            	
            }
            else{
            	this.$('.prev').hide();            	
            }
            if(this.collection.hasNext()){
            	this.$('.next').show();            	
            }
            else{
            	this.$('.next').hide();            	
            }
            //this.footer.render();
            //this.$footer.html(this.footer.render().el);
        } else {
        	this.$('.next, .prev').hide();
            this.$header.hide();
            this.$footer.hide();
        }
    },
    refresh : function() {
    	'use strict';
    	var view;
    	while(this.rows.length){
    		view = this.rows.pop();
    		view.remove();
    	}
        //this.$('tbody').empty();
        this.collection.each(this.insertRow, this);        	
        //this.render();
    },
    clearUidFilter: function(){
    	App.eventsFilter.clearUidFilter();
    },
    clearDateFilter: function(){
    	App.eventsFilter.clearDateFilter();
    },
    nextPage: function(){
    	'use strict';
    	var view, next;
    	function whenLoaded(){
			this.$el.removeClass('loading');
			this.refresh();
    	}
    	if(this.collection.hasNext()){
    		this.$el.addClass('loading');
    		next = this.collection.getNextPage();
    		if('done' in next){
    			next.done(whenLoaded.bind(this));
    		}
    		else{
    			whenLoaded.call(this);
    		}
    		App.appRouter.updateUrl();    		
    	}
    },
    previousPage: function(){
    	'use strict';
    	var view;
    	if(this.collection.hasPrevious()){
        	this.collection.getPreviousPage();
        	App.appRouter.updateUrl();    		        			
        	this.refresh();
    	}
    }
});

/* The DOM element for an individual EventLog */
App.EventView = Backbone.View.extend({
    tagName : 'tr',

    // Cache the template function for a single item.
    template : _.template($('#event-row-template').html()),

    // The DOM events specific to an item.
    events : {
    	'click .devicetype': 'selectUid',
    	'click .date': 'selectDate',
    	'click .count':'viewLog'
        //'dblclick label': 'edit',
        //'keypress .edit': 'updateOnEnter',
        //'blur .edit': 'close'
    },
    initialize : function() {'use strict';
        this.listenTo(this.model, 'change', this.render);
        this.$el.attr('data-cid',this.model.cid);
        this.count = this.model.count.bind(this.model);
        this.durations = this.model.durations.bind(this.model);
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
    	App.eventsFilter.setUidFilter(this.model.get('uid'));
    },
    selectDate: function(ev){
    	'use strict';
    	App.eventsFilter.setDateFilter(this.model.get('date'));
    },
    viewLog: function(ev){
    	'use strict';
    	App.appRouter.viewLog(this.model);
    }
});

App.LogTotalsView = Backbone.View.extend({
    //tagName : 'div',
    // Cache the template function for a single item.
    initialize : function(options) {'use strict';
    	options = options || {};
        /*this.$header = this.$('.header');
        this.$footer = this.$('.footer');
        this.dateList = [];
        this.listenTo(App.eventLogs.fullCollection, 'add', this.addOne);
        this.listenTo(App.eventLogs.fullCollection, 'reset', this.addAll);*/
    	this.template = _.template($(options.template).html());
    	this.collection = options.collection;
        this.listenTo(this.collection, 'change add remove', this.render);
    },
    render : function() {'use strict';
        var self = this, context={};
        //console.log('render totals');
        context.totalCount = this.countEvents('start', this.itemFilter);
        ['cloud', 'upnp', 'zeroconf','end'].forEach(function(name) {
            context[name + 'Count'] = self.countEvents(name, self.itemFilter);
            context[name + 'Duration'] = self.duration(name, self.itemFilter);
        });
        this.$el.html(this.template(context));
        return this;
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
        this.collection.filter(filter).forEach(function(item) {
        	var t;
        	if(typeof(item.durations)=='function'){
        		t = item.durations(event);
        	}
        	else{
        		t = item.get('durations')(event);
        	}
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
    countEvents : function(event,filter) {'use strict';
        'use strict';
        var rv = 0;
        if(filter===undefined){
        	filter = function(){return true;};
        }
        this.collection.filter(filter).forEach(function(item) {
        	if(typeof(item.count)=='function'){
                rv += item.count(event);        		
        	}
        	else{
        		rv += item.get('count')(event);
        	}
        });
        //console.log('count '+event+'='+rv+' '+this.collection.length);
        return rv;
    }
});

App.EventDetailView = Backbone.View.extend({
	tagName:'article',
	template : _.template($('#event-detail-template').html()),
	events: {
		'click .back' : 'viewSummary'
	},
	initialize: function(options){
		//this.model 
        this.listenTo(this.model, 'change', this.render);
	},
	render: function(){
		'use strict';
		var j, ev, script, start, entries, entry, attributes = $.extend({},this.model.toJSON());
		start=null;
		function pollMapsAPI(){
			delete App.pollMapsAPI;
			if(('google' in window) && ('maps' in window.google) && ('LatLng' in window.google.maps) ){
				attributes.mapAPI.resolve();
			}
			else if(('google' in window) && ('maps' in window.google) ){
				/* main maps API script has loaded, waiting for sub-scripts to load */
				setTimeout(pollMapsAPI,500);
			}
			else{
				App.pollMapsAPI = pollMapsAPI;
				script = document.createElement('script');
				script.type = 'text/javascript';
				script.src = "https://maps.googleapis.com/maps/api/js?v=3.exp&key=AIzaSyCGHHsMx3K8yXH7aBg-GBQWm1NPgM4xXq4&sensor=false&callback=App.pollMapsAPI";
				document.body.appendChild(script);
			}
		}
		
		if(this.model.attributes.loc && (this.model.attributes.loc.lat || this.model.attributes.loc.lon)){
			attributes.mapAPI = $.Deferred();
			pollMapsAPI();
		}
		entries = this.model.get('entries');
		attributes.entries = [];
		for(j=0; j<entries.length; ++j){
			if(entries[j] instanceof Backbone.Model){
				entry  = entries[j].toJSON();
			}
			else{
				entry = { ts:entries[j].ts, ev:entries[j].ev };
			}
            if(entry.ev=='start' || start===null){
                start = entry.ts;
                entry.start=true;
            }
            else if(start){
            	entry.diff = entry.ts.diff(start) / 1000.0;
            }
            if(entry.ev=='end'){
            	entry.end=true;
            	start=null;
            }
            attributes.entries.push(entry);
		}
		if(attributes.entries.length && attributes.entries[attributes.entries.length-1].ev!='end'){
			attributes.entries[attributes.entries.length-1].end=true;
		}
        this.$el.html(this.template(attributes));
        if(attributes.mapAPI){
        	attributes.mapAPI.done(function(){
        		var mapOptions = {
        				center: new google.maps.LatLng(attributes.loc.lat, attributes.loc.lon),
        				zoom: 12,
        				mapTypeId: google.maps.MapTypeId.ROADMAP
        		};
        		google.maps.visualRefresh = true;
        		var map = new google.maps.Map(document.getElementById("map-canvas"), mapOptions);
        		new google.maps.Marker({
        			map: map,
        			position: mapOptions.center
        		});
        	});
        }
        return this;
	},
	viewSummary: function(){
    	'use strict';
    	App.appRouter.viewSummary();		
	}
});
