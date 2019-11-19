function ScormXBlock(runtime, element, settings) {
  var $scormIframe = $("iframe", element);

  function SCORM_12_API(){

    this.LMSInitialize = function(){
      return "true";
    };

    this.LMSFinish = function() {
      return "true";
    };

    this.LMSGetValue = GetValue;
    this.LMSSetValue = SetValue;

    this.LMSCommit = function() {
        return "true";
    };

    this.LMSGetLastError = function() {
      return "0";
    };

    this.LMSGetErrorString = function(errorCode) {
      return "Some Error";
    };

    this.LMSGetDiagnostic = function(errorCode) {
      return "Some Diagnostice";
    }
  }

  function SCORM_2004_API(){
    this.Initialize = function(){
      return "true";
    };

    this.Terminate = function() {
      return "true";
    };

    this.GetValue = GetValue;
    this.SetValue = SetValue;

    this.Commit = function() {
        return "true";
    };

    this.GetLastError = function() {
      return "0";
    };

    this.GetErrorString = function(errorCode) {
      return "Some Error";
    };

    this.GetDiagnostic = function(errorCode) {
      return "Some Diagnostice";
    }
  }

  var GetValue = function (cmi_element) {
    var handlerUrl = runtime.handlerUrl(element, 'scorm_get_value');

    var response = $.ajax({
      type: "POST",
      url: handlerUrl,
      data: JSON.stringify({'name': cmi_element}),
      async: false
    });
    response = JSON.parse(response.responseText);
    return response.value
  };

  var SetValue = function (cmi_element, value) {
    if (cmi_element === 'cmi.core.exit' || cmi_element === 'cmi.exit') {
      closeFullScreenScorm();
    }

    var handlerUrl = runtime.handlerUrl( element, 'scorm_set_value');

    $.ajax({
      type: "POST",
      url: handlerUrl,
      data: JSON.stringify({'name': cmi_element, 'value': value}),
      async: false,
      success: function(response){
        if (typeof response.lesson_score != "undefined"){
          $(".lesson_score", element).html(response.lesson_score);
        }
        $(".completion_status", element).html(response.completion_status);
      }
    });

    return "true";
  };

  function closeFullScreenScorm(event) {
    if (event === undefined || event.keyCode === 27) {
      $scormIframe.removeClass("full-screen-scorm");
      $(document).off('keydown', closeFullScreenScorm);
      $($scormIframe[0].contentDocument).off('keydown', closeFullScreenScorm);
    }
  }

  $(function ($) {
    if (settings.version_scorm == 'SCORM_12') {
      API = new SCORM_12_API();
    } else {
      API_1484_11 = new SCORM_2004_API();
    }

    $('.scorm_launch', element).on( "click", function() {
      $scormIframe.addClass("full-screen-scorm");
      $(document).on('keydown', closeFullScreenScorm);
      $($scormIframe[0].contentDocument).on('keydown', closeFullScreenScorm);
    });
  });
}
