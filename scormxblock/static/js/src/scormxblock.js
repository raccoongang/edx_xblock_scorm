function ScormXBlock(runtime, element, settings) {

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
      $(".js-scorm-block", element).removeClass('full-screen-scorm');
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

  $(function ($) {
    if (settings.version_scorm == 'SCORM_12') {
      API = new SCORM_12_API();
    } else {
      API_1484_11 = new SCORM_2004_API();
    }

    var $scormBlock = $(".js-scorm-block", element);
    $('.js-button-full-screen', element).on( "click", function() {
      $scormBlock.toggleClass("full-screen-scorm");
    });
  });

  const $links = $('.scorm-structure-navigation-body-link'),
        $closeMenu = $('.close-navigation'),
        $activeClass = 'current';
  let linkIndex = 1,
      linkToShow = $links.eq(linkIndex - 1).attr('href');

  $closeMenu.on('click', function () {
    $(this).toggleClass('hide');
    $(this).hasClass('hide') ? $closeMenu.text(gettext('Show menu')) : $closeMenu.text(gettext('Close menu'));
    $('.scorm-structure').toggle();
  });

  $('.scorm-structure-navigation-head').on('click', function () {
    $(this).next().slideToggle();
  });

  $links.each(function (i) {
    $(this).attr('data-id', ++i);
  });

  showLinks(linkIndex, linkToShow);

  function showLinks(n, src) {
    $('.scorm_object').attr('src', src);
    $links.each(function () {
      $(this).removeClass($activeClass);
    });
    $links.eq(n - 1).addClass($activeClass);
  }

  function plusLinks(n) {
    let currentLink = $(`.${$activeClass}`).attr('data-id'),
        currentID = parseInt(currentLink),
        nextLinkID = currentID += n;

    if (nextLinkID > $links.length) {
      nextLinkID = 1;
    } else if (nextLinkID < 1) {
      nextLinkID = $links.length;
    }

    $(`.${$activeClass}`).closest($('.scorm-structure-navigation-body')).css('display', 'block');
    const nextLinkSrc = $links.eq(nextLinkID - 1).attr('href');
    showLinks(nextLinkID, nextLinkSrc);
  }

  $('.link-prev').on('click', () => plusLinks(-1));
  $('.link-next').on('click', () => plusLinks(1));
  $('.link-first').on('click', () => plusLinks($links.length));
  $('.link-last').on('click', () => plusLinks(-$links.length));

  $links.each(function () {
    $(this).on('click', (e) => {
      e.preventDefault();
      const linkSrc = $(this).attr('href'),
          ID = $(this).attr('data-id');
      showLinks(ID, linkSrc);
    });
  });
}
