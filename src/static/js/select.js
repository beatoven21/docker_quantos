// Initialize Select2 on the select element
$("#dropColsSelect").select2();
// Add the functionality of the "Clear" button
$("#clearBtn").click(function(){
    $("#dropColsSelect").val(null).trigger("change");
});
// Add the functionality of the "Drop" button
document.getElementById("dropBtn").addEventListener("click", function(){
    document.querySelector("#selectBox #form").submit();
});
// Enable "Drop" & "Clear" button only if columns to drop are selected
$("#dropColsSelect").on("change", function() {
  if($(this).val().length) {
    $("#dropBtn").prop("disabled", false);
    $("#clearBtn").prop("disabled", false);
  } else {
    $("#dropBtn").prop("disabled", true);
    $("#clearBtn").prop("disabled", true);  }
});