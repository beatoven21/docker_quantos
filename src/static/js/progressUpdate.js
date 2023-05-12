function updateProgress() {
    setInterval(function() {
        $.ajax({
          url: '/progress',
          type: 'GET',
          success: function(data) {
            // update the progress bar with the received data
            $('#progress-bar').css('width', data.progress + '%');
            // update the text with the received data
            $('#progress-bar').text(data.progress + '%');
          },
          error: function(error) {
            console.error(error);
          }
        });
    }, 2000);
}


