document.addEventListener("DOMContentLoaded", () => {
  const asideToggleContainer = document.querySelector("[data-aside-toggle]");

  const asideToggleButtons = document.querySelectorAll(
    "[data-aside-toggle-button]",
  );

  asideToggleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      asideToggleContainer.classList.toggle("collapsed");
    });
  });
});
