import $ from "jquery";
import { initAll } from "govuk-frontend";
import TabSet from "./components/tabSet";
import "./components/document_navigation_links";

(function ($) {
  $.fn.manage_filters = function (options) {
    const settings = $.extend({}, $.fn.manage_filters.defaults, options);
    return this.each(() => {
      const $toggle_area = $(".js-results-facets", $(this));

      const $control_container = $(".js-results-control-container", $(this));

      const btn = $("<button>", {
        class: "results-search-component__toggle-control",
        type: "button",
        text: settings.expanded_text,
        click: (e) => {
          $toggle_area.toggle();

          const $el = $(e.target);

          $el.toggleClass("collapsed");

          $el.text(() => {
            return $el.text() === settings.collapsed_text
              ? settings.expanded_text
              : settings.collapsed_text;
          });
        },
      });

      if (settings.initially_hidden) {
        btn.trigger("click");
      }

      $control_container.append(btn);
    });
  };

  $.fn.manage_filters.defaults = {
    collapsed_text: "Show filter options",
    expanded_text: "Hide filter options",
    initially_hidden: true,
  };
})($);

$(".js-results-facets-wrapper").manage_filters();

$(".judgment-toolbar__delete").click(() =>
  confirm(
    "Are you sure you want to delete this judgment? Deletion is permanent.",
  ),
);

$("#judgment-toolbar__more-button").show();
$(".judgment-toolbar__more").hide();

$("#judgment-toolbar__more-button").on("click", function () {
  $(".judgment-toolbar__more").slideToggle();
  $("#judgment-toolbar__more-button").toggleClass("toggled");
});

$(".document-history__event-debug-toggle").on("click", function () {
  $("#event-debug-v" + $(this).data("target-event")).toggle();
});

$(".document-history__submission-toggle").on("click", function () {
  $("#submission-" + $(this).data("target-submission")).toggle();
});

TabSet.init();

initAll();
