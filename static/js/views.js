(function() {
    var requestAnimationFrame = window.requestAnimationFrame || window.mozRequestAnimationFrame || window.webkitRequestAnimationFrame || window.msRequestAnimationFrame;
    if (requestAnimationFrame === undefined) {
        window.requestAnimationFrame = function(callback) {
            return setTimeout(callback, 1000 / 60);
        }
    } else if (!( requestAnimationFrame in window)) {
        window.requestAnimationFrame = requestAnimationFrame;
    }
})();

/*  **AppView** is the top-level piece of UI. */
App.EventsListView = Backbone.View.extend({
    el : '#EventsListView',
    events : {
        'click .back' : 'clearFilter',
        'click .next' : 'nextPage',
        'click .prev' : 'previousPage'
    },
    initialize : function() {
        this.$header = this.$('thead');
        this.$footer = this.$('tfoot');
        this.rows = new Backbone.Collection([], {
            model : App.EventView
        });
        this.footer = new App.LogTotalsView({
            collection : this.rows,
            template : '#event-foot-template', /*tagName:'tr' */
            el : '#events tfoot'
        });
        this.footer.$el.addClass('totals');
        this.need_redraw = false;
        this.listenTo(this.collection, "add", this.insertRow);
        this.listenTo(this.collection, "remove", this.removeRow);
        this.listenTo(this.collection, "sort", this.refresh);
        this.listenTo(this.collection.fullCollection, "reset", this.refresh);
        this.listenTo(App.eventsFilter, 'change', this.refresh);
        //this.listenTo(this.collection.fullCollection, "filter", this.refresh);
        //this.listenTo(this.collection.fullCollection, "add", this.addOne);
        //this.listenTo(this.collection, 'add', this.addOne);
        //this.listenTo(this.collection, 'reset', this.addAll);
        //this.listenTo(this.collection, 'all', this._requestRedraw);
        //this.on('selectDate', this.addAll);
        //this.listenTo(this.collection,'filter', this.addAll);
    },
    insertRow : function(model, collection, options) {'use strict';
        var view, $el, $children, $rowEl, index;
        if (!App.eventsFilter.itemFilter(model)) {
            return this;
        }
        if (collection === undefined || typeof (collection) == 'number') {
            collection = this.collection;
        }
        index = collection.indexOf(model);
        //console.log('Add '+model.cid+' '+index);
        view = new App.EventView({
            model : model
        });
        this.rows.add(view, {
            at : index
        });
        //this.rows.splice(index, 0, view);
        $el = this.$('tbody');
        $children = $el.children();
        $rowEl = view.render().$el;
        options = _.extend({
            render : true
        }, options || {});
        if (options.render) {
            if (index >= $children.length) {
                $el.append($rowEl);
            } else {
                $children.eq(index).before($rowEl);
            }
            this._requestRedraw();
        }
        return this;
    },
    removeRow : function(model, collection, options) {'use strict';
        var view;
        if (options.index < this.rows.length && this.rows[options.index].model.id == model.id) {
            console.log('Remove ' + model.cid + ' ' + options.index);
            view = this.rows[options.index];
            this.rows.remove(view);
            //view = this.rows.splice(options.index, 1);
            //this.$('[data-cid="'+model.cid+'"]').remove();
            //view[0].remove();
            this._requestRedraw();
        }
    },
    _requestRedraw : function() {
        if (!this.need_redraw) {
            this.need_redraw = true;
            requestAnimationFrame(this.render.bind(this));
        }
    },
    render : function() {'use strict';
        var self = this, context = {}, noFilter;
        this.need_redraw = false;
        if (this.collection.length) {
            this.$header.show();
            this.$footer.show();
            noFilter = App.eventsFilter.isEmpty();
            if (this.collection.hasPrevious() && noFilter) {
                this.$('.prev').show();
            } else {
                this.$('.prev').hide();
            }
            if (this.collection.hasNext() && noFilter) {
                this.$('.next').show();
            } else {
                this.$('.next').hide();
            }
            if (!noFilter) {
                this.$('.back').show();
            } else {
                this.$('.back').hide();
            }
            //this.footer.render();
            //this.$footer.html(this.footer.render().el);
        } else {
            this.$('.next, .prev').hide();
            this.$header.hide();
            this.$footer.hide();
        }
    },
    refresh : function() {'use strict';
        var view;
        while (this.rows.length) {
            view = this.rows.pop();
            view.remove();
        }
        //this.$('tbody').empty();
        this.collection.each(this.insertRow, this);
        //this.render();
    },
    clearFilter : function() {
        App.eventsFilter.clear();
    },
    nextPage : function() {'use strict';
        var view, next;
        function whenLoaded() {
            this.$el.removeClass('loading');
            this.refresh();
        }

        if (this.collection.hasNext()) {
            this.$el.addClass('loading');
            next = this.collection.getNextPage();
            if ('done' in next) {
                next.done(whenLoaded.bind(this));
            } else {
                whenLoaded.call(this);
            }
            App.appRouter.updateUrl();
        }
    },
    previousPage : function() {'use strict';
        var view;
        if (this.collection.hasPrevious()) {
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
        'click .devicetype' : 'selectUid',
        'click .description' : 'selectUid',
        'click .date' : 'selectDate',
        'click .count' : 'viewLog',
        'click .time' : 'viewLog'
        //'dblclick label': 'edit',
        //'keypress .edit': 'updateOnEnter',
        //'blur .edit': 'close'
    },
    initialize : function() {'use strict';
        this.listenTo(this.model, 'change', this.render);
        this.$el.attr('data-cid', this.model.cid);
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
    selectUid : function(ev) {'use strict';
        App.appRouter.viewUid(this.model.get('uid'));
    },
    selectDate : function(ev) {'use strict';
        App.appRouter.viewDate(this.model.get('date'));
    },
    viewLog : function(ev) {'use strict';
        App.appRouter.viewLog(this.model);
    }
});

App.LogTotalsView = Backbone.View.extend({
    //tagName : 'div',
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
        var self = this, context = {};
        //console.log('render totals');
        context.totalCount = this.countEvents('start');
        ['cloud', 'upnp', 'zeroconf', 'end'].forEach(function(name) {
            context[name + 'Count'] = self.countEvents(name);
            context[name + 'Duration'] = self.duration(name);
        });
        this.$el.html(this.template(context));
        return this;
    },
    /**
     *  calculates the average time taken for each of the given discovery method
     * @param {string} event The name of the event type ("start", "upnp", "zeroconf", "cloud")
     */
    duration : function(event, filter) {'use strict';
        var avg, times = [];
        if (filter === undefined) {
            filter = function() {
                return true;
            };
        }
        this.collection.filter(filter).forEach(function(item) {
            var t;
            if ( typeof (item.durations) == 'function') {
                t = item.durations(event);
            } else {
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
    countEvents : function(event, filter) {'use strict';'use strict';
        var rv = 0;
        if (filter === undefined) {
            filter = function() {
                return true;
            };
        }
        this.collection.filter(filter).forEach(function(item) {
            if ( typeof (item.count) == 'function') {
                rv += item.count(event);
            } else {
                rv += item.get('count')(event);
            }
        });
        //console.log('count '+event+'='+rv+' '+this.collection.length);
        return rv;
    }
});

/**
 * View for showing the details of one log entry
 */
App.EventDetailView = Backbone.View.extend({
    tagName : 'article',
    template : _.template($('#event-detail-template').html()),
    events : {
        'click .back' : 'viewSummary',
        'click .location' : 'showMap'
    },
    initialize : function(options) {
        //this.model
        this.listenTo(this.model, 'change', this.render);
        this.$el.addClass('eventdetail');
    },
    render : function() {'use strict';
        var j, ev, start, entries, entry, attributes = $.extend({}, this.model.toJSON());
        start = null;

        /*if(this.model.attributes.loc && (this.model.attributes.loc.lat || this.model.attributes.loc.lon)){
         attributes.mapAPI = $.Deferred();
         pollMapsAPI();
         }*/
        entries = this.model.get('entries');
        attributes.entries = [];
        for ( j = 0; j < entries.length; ++j) {
            if (entries[j] instanceof Backbone.Model) {
                entry = entries[j].toJSON();
            } else {
                entry = {
                    ts : entries[j].ts,
                    ev : entries[j].ev
                };
            }
            if (entry.ev == 'start' || start === null) {
                start = entry.ts;
                entry.start = true;
            } else if (start) {
                entry.diff = entry.ts.diff(start) / 1000.0;
            }
            if (entry.ev == 'end') {
                entry.end = true;
                start = null;
            }
            attributes.entries.push(entry);
        }
        if (attributes.entries.length && attributes.entries[attributes.entries.length - 1].ev != 'end') {
            attributes.entries[attributes.entries.length - 1].end = true;
        }
        this.$el.html(this.template(attributes));
        return this;
    },
    viewSummary : function() {'use strict';
        App.appRouter.viewSummary();
    },
    showMap : function() {'use strict';
        var mapPromise, self = this;

        function pollMapsAPI() {
            var callback, script;
            if (mapPromise.callbackName) {
                delete window[mapPromise.callbackName];
                delete mapPromise.callbackName;
            }
            delete App.pollMapsAPI;
            if (('google' in window) && ('maps' in window.google) && ('LatLng' in window.google.maps)) {
                mapPromise.resolve();
            } else if (('google' in window) && ('maps' in window.google)) {
                /* main maps API script has loaded, waiting for sub-scripts to load */
                setTimeout(pollMapsAPI, 500);
            } else {
                callback = 'pollMapsAPI' + Date.now();
                while ( callback in window) {
                    callback += Math.floor(Math.random() * 10);
                }
                mapPromise.callbackName = callback;
                window[callback] = pollMapsAPI;
                script = document.createElement('script');
                script.type = 'text/javascript';
                script.src = "https://maps.googleapis.com/maps/api/js?v=3.exp&key=AIzaSyCGHHsMx3K8yXH7aBg-GBQWm1NPgM4xXq4&sensor=false&callback=" + callback;
                document.body.appendChild(script);
            }
        }

        if (this.$(".mapcanvas").length) {
            return;
        }
        mapPromise = $.Deferred();
        this.$el.append($('<div>', {
            'class' : "mapcanvas"
        }));
        if (this.model.attributes.loc && (this.model.attributes.loc.lat || this.model.attributes.loc.lon)) {
            pollMapsAPI();
            mapPromise.done(function() {
                var mapOptions = {
                    center : new google.maps.LatLng(self.model.attributes.loc.lat, self.model.attributes.loc.lon),
                    zoom : 12,
                    mapTypeId : google.maps.MapTypeId.ROADMAP
                };
                google.maps.visualRefresh = true;
                var map = new google.maps.Map(self.$(".mapcanvas")[0], mapOptions);
                new google.maps.Marker({
                    map : map,
                    position : mapOptions.center
                });
            });
        }
    }
});
