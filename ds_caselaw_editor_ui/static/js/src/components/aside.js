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
