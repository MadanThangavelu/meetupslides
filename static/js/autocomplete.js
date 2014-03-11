$(document).ready(function() {
    $("#meetups_list").autocomplete({
        source: "/autocomplete/meetups",
        minLength: 2,
        
        select: function(event, ui) {
            var meetup_id = ui.item.id;
            if(meetup_id != '#') {
                location.href = '/meetup/' + meetup_id;
            }
        },
                                     
        // html: true, // optional (jquery.ui.autocomplete.html.js required)
 
      // optional (if other layers overlap autocomplete list)
        open: function(event, ui) {
            $(".ui-autocomplete").css("z-index", 1000);
        }
    });
 
});