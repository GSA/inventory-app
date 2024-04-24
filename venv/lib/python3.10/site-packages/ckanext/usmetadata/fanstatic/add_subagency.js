/**
 * Created by ykhadilkar on 11/19/14.
 */
$(document).ready(function(){
    for( var i=1; i<6; i++){
        if($('#field-publisher_'+i).val() === ""){
            $('.field-publisher_'+i).hide()
        }
    }

    $("#add-sub-agency").click(function(){
        for( var i=1; i<6; i++) {
            if (!$('.field-publisher_'+i).is(":visible")) {
                $('.field-publisher_'+i).show();
                break;
            }
        }
    });
});