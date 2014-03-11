var show_add_meetup = function(event) {
    event.preventDefault();
    $('#add_meetup_wrapper').toggle();
};

var add_meetup = function() {
    var meetup_name = $('#meetup_name', $(this).parent()).val();
    var meetup_city = $('#meetup_city', $(this).parent()).val();
    $.post("/meetup/add", { ajax:1, meetup_name: meetup_name, meetup_city: meetup_city },
        function(data) {
            select_meetup(data);
        });
};

var select_meetup = function(data) {
    var meetup_name = data.name + ' ' + data.city;
    $('#meetup_id').append(
        $('<option></option>').val(data.id).html(meetup_name)
    );
    $('#meetup_id').val(data.id);
    $('#add_meetup_wrapper').hide();
};


SubmitLink = {
    save_and_update_ui: function(obj){                                            
       console.log(obj["url"]);
       console.log(obj["speaker_name"]);
       console.log(obj["presentation_title"]);
       console.log(obj["description"]);
       console.log(obj["slide_date"]);
       var meetup_id= $('#hidden_field_for_meetup_id').html();  
       obj["meetup_id"] = meetup_id
       $.post( "/add_slide", obj, function(a){ 
            // Let us render the data back into a html and give it to front end at this point :/                                                         
            SubmitLink.add_new_upload_to_list(a);
       });                          
    },   
              
    add_new_upload_to_list: function(a){
      // Append this information to beginning of the list of blockquotes
      $(a.replace(/^\s+|\s+$/g, ''))
      .hide()
      .prependTo(".slides-container")
      .slideDown('slow')
      .animate({opacity: 1.0})
      .addClass("new_item");
    }          
                
}
// New stuff
$(document).ready(function(){
    $(".datepicker").datepicker();  
    $("#slide_link_submit").click(function(){
       var url = $("#slide_url").val();
       var speaker_name = $("#slide_author").val();
       var presentation_title = $("#slide_presentation_title").val();
       var presentation_description = $("#slide_description").val();        
       var presentation_date = $("#slide_presentation_date").val();
       SubmitLink.save_and_update_ui({url:url, 
                                      speaker_name:speaker_name,
                                      presentation_title:presentation_title,
                                      presentation_description:presentation_description,
                                      presentation_date:presentation_date,
                                      post_type:"slide"
       });                                     
    });
                             
    $("#video_link_submit").click(function(){
       var url = $("#video_url").val();
       var speaker_name = $("#video_author").val();
       var presentation_title = $("#video_presentation_title").val();
       var presentation_description = $("#video_description").val();        
       var presentation_date = $("#video_presentation_date").val();
       SubmitLink.save_and_update_ui({url:url, 
                                      speaker_name:speaker_name,
                                      presentation_title:presentation_title,
                                      presentation_description:presentation_description,
                                      presentation_date:presentation_date,
                                      post_type:"video"
       });                                     
    });    
});
