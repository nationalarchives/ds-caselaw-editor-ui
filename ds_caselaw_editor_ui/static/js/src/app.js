import $ from "jquery";

import TabSet from "./components/tabSet";
import JudgmentSidebar from "./components/judgmentSidebar";

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
    "Are you sure you want to delete this judgment? Deletion is permanent."
  )
);

$(".judgments-list__judgment-assign-form").on("submit", function (event) {
  event.preventDefault();
  const form = $(this);
  const uri = form.find("input[name='judgment_uri']").val();
  const action = form.attr("action");
  const loading = $(
    "<span class='loading-indicator' role='progressbar' aria-valuetext='Loading' aria-busy='true' aria-live='polite'></span>"
  );
  form.replaceWith(loading);
  $.ajax({
    type: "POST",
    url: action,
    data: form.serialize(),
    success: function (data) {
      const assigned_to = data["assigned_to"];
      loading.replaceWith(
        "<a aria-busy='false' href='/" +
          encodeURIComponent(uri) +
          "/edit#assigned_to'>" +
          assigned_to +
          "</a>"
      );
    },
  });
});

TabSet.init();
JudgmentSidebar.init();
