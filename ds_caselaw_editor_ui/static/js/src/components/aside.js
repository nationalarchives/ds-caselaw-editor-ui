document.addEventListener("DOMContentLoaded", () => {
  const asideToggleContainer = document.querySelector("[data-aside-toggle]");
  if (!asideToggleContainer) return;

  const asideToggleButtons = asideToggleContainer.querySelectorAll(
    "[data-aside-toggle-button]",
  );

  asideToggleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      asideToggleContainer.classList.toggle("collapsed");
    });
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const asideEditContainer = document.querySelector("[data-aside-edit]");
  if (!asideEditContainer) return;

  const asideEditShowButtons = asideEditContainer.querySelectorAll(
    "[data-aside-edit-show-button]",
  );

  const asideEditHideButtons = asideEditContainer.querySelectorAll(
    "[data-aside-edit-hide-button]",
  );

  asideEditShowButtons.forEach((button) => {
    button.addEventListener("click", () => {
      asideEditContainer.classList.toggle("editing");
    });
  });

  asideEditHideButtons.forEach((button) => {
    button.addEventListener("click", () => {
      asideEditContainer.classList.toggle("editing");
    });
  });
});
