var Meetup = Backbone.Model.extend({
    initialize: function(){
        //console.log("Welcome to this world" + this.id);
    }                                                                            
});


var Meetups = Backbone.Collection.extend({
    model: Meetup,
    url: '/meetups'
});

meetups = new Meetups();

var MeetupView = Backbone.View.extend({ 
   initialize : function(){
                                 
   },  
                                       
   render : function(){
     console.log("called render for individual meetup view")                    
   }                                                                                                                    
});


var MeetupsListView = Backbone.View.extend({
     collection: meetups,
     el: $('ul#meetup-list'),
     
     initialize : function(){
      _(this).bindAll('add');
      this.collection.bind('add', this.add);
      
                                   
       var that = this;
       this._meetupViews = []; 
       this.collection.each(function(meetup) {
        console.log("adding meetup views");                                      
        that._meetupViews.push(                                    
                  new MeetupView({
                                  model: meetup                                  
                                })                          
        )});
    },
                                            
     add : function(meetup) {
          console.log("Add called");                 
          var m = new MeetupView({
                                  model: meetup                                  
                                });
                           
          this._meetupViews.push(m);  
          if (this._rendered) {
             console.log("going to render and append individual element");
             $(this.el).append(m.render().el);                               
          }else{
             console.log("_NOT_ going to render and append individual element");   
          }                             
     },     
                                                                                    
     render : function(){
        console.log("collection render called");
         var that = this;
         $(this.el).empty();
         _(this._meetupViews).each(function(dv){
                $(that.el).append(dv.render().el);                                                
         });                  
     }                                                                                         
});

var meetupListView = new MeetupsListView();
meetupListView.render();

meetups.fetch({
success: function(collection, response, options){
        //console.log('Collection fetch success', response.meetups);
        //console.log('Collection models: ', meetups.models);                                                
}});


                                        