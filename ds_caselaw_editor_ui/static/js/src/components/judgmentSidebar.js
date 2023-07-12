import $ from "jquery";

const JudgmentSidebar = {
  init: function () {
    const elements = $(".judgment-sidebar");
    elements.each(function (ix, element) {
      JudgmentSidebar.initOne(element);
    });
  },

  initOne: function (element) {
    JudgmentSidebar.initAssignForm(element);
  },

  initAssignForm: function (element) {
    const form = $(element).find(".judgment-sidebar__judgment-assign-form");
    const select = form.find("select");
    const submit = form.find("input[type='submit']");
    submit.hide();
    select.on("change", function (event) {
      form.find(".judgment-sidebar__context-notification").remove();
      form.trigger("submit");
    });
    form.on("submit", function (event) {
      event.preventDefault();
      const form = $(this);
      const action = form.attr("action");
      const loading = $(
        "<span class='loading-indicator' role='progressbar' aria-valuetext='Loading' aria-busy='true' aria-live='polite'></span>",
      );
      form.append(loading);
      $.ajax({
        type: "POST",
        url: action,
        data: form.serialize(),
        success: function (data) {
          const successMessage = $(
            "<div class='context-notification--success judgment-sidebar__context-notification' aria-busy='false' />",
          );
          successMessage.text(data["message"]);
          loading.replaceWith(successMessage);
        },
      });
    });
  },
};

export default JudgmentSidebar;
