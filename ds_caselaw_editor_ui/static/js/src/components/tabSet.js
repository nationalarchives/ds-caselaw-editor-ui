import $ from "jquery";

const TabSet = {
  init: function () {
    const elements = $(".tabs-set");
    elements.each(function (ix, element) {
      TabSet.initOne(element);
    });
  },

  initOne: function (container) {
    const items = $(container).find(".tabs-set__item");
    items.each(function (ix, item) {
      const a = $(item).find("a");
      const input = $(item).find("input");
      a.on("click", function () {
        input.prop("checked", true);
      });
    });
  },
};

export default TabSet;
