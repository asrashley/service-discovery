$(document).ready(function(){
    'use strict';
    function formatTime(time){
        var hrs = ('00'+time.getHours()).slice(-2);
        var mins = ('00'+time.getMinutes()).slice(-2);
        var secs = ('00'+time.getSeconds()).slice(-2);
        return [hrs,mins,secs].join(':');
    }
    function backToSummary(ev){
        ev.preventDefault();
        $('#detail').remove();
        $('#summary').css('display','block');
        return false;
    }
    
    var eventLogs = JSON.parse($('#eventjson').text());
    $('td.count').addClass('clickable').on('click',function(ev){
    	ev.preventDefault();
    	var i, j, date, detail, uid, ev, start, table, heading, ts, rcol, extra, row = $(this).parent();
    	uid=row.data('uid');
    	date = row.data('date');
    	extra = row.find('.popup').html();
    	for(i=0; i<eventLogs.length; ++i){
    		if(eventLogs[i].uid==uid && eventLogs[i].date==date){
    			/*console.dir(eventLogs[i]); */
                $('#summary').css('display','none');
    			detail = $('<div>', {'id':'detail'});
                j = $('<a>', {'class':'back', href:"#"}).text('Back to summary').on('click', backToSummary);
                detail.append(j)
                heading = ['Logging events for'];
                if(row.data('client')=="true"){
                	heading.push('client');
                }
                else{
                	heading.push('device');
                }
                if(row.data('name')){
                	heading.push(row.data('name'));
                }
                else{
                	heading.push(uid);
                }
                heading.push('on');
                heading.push(date);
                heading = heading.join(' ');
            	detail.append($('<h2>').text(heading));
    			detail.append($('<div>', {'class':'leftcol'}).html($('<table>').html(extra)));
    			rcol = $('<div>', {'class':'rightcol'});
    			table=null;
    			start=null;
    			for(j=0; j<eventLogs[i].events.length; ++j){
                    row = $('<tr>');
                    ev = eventLogs[i].events[j];
                    ts = new Date(ev.ts);
                    if(ev.ev=='start' || start===null){
                    	if(table!=null){
                            rcol.append(table);
                            table=null;
                    	}
                        start = ts.getTime();
                    }
                    row.append($('<td>').text(ev.ev));                      
                    if(ev.ev=='start'){
                        row.append($('<td>').text(formatTime(ts)));
                    }
                    else{
                        row.append($('<td>').text('+'+(ts.getTime()-start)/1000.0));                    	
                    }
    				if(table===null){
    				    table = $('<table>', {'class':'eventlog'});
    				}
                    table.append(row);
    			}
    			if(table!==null){
    			    rcol.append(table);
    			}
    			detail.append(rcol);
                $('#logging').append(detail);
    		}
    	}
    	return false;
    });
});