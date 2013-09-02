var styleDOM = $("#mystyle");
var bodyDOM;
var id;

var counter = 0;
function loadNextFrame(){
    var curData = DATA[counter++];
    if (typeof curData === 'undefined'){
        window.clearInterval(id);
        return;
    }

    styleDOM.html(curData.style);
    bodyDOM.html(curData.body);
}

$(document).on('ready', function(){
    $.getJSON('data.json', function(data){
        DATA_LEN = Object.keys(data).length;
        DATA = data;
        bodyDOM = $("body");

        id = window.setInterval(loadNextFrame, 200);
    });

});
