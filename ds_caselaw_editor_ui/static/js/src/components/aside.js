document.addEventListener("DOMContentLoaded", () => {
  const asideToggleContainer = document.querySelector("[data-aside-toggle]");
  if (asideToggleContainer) {
    const asideToggleButtons = asideToggleContainer.querySelectorAll(
      "[data-aside-toggle-button]",
    );

    asideToggleButtons.forEach((button) => {
      button.addEventListener("click", () => {
        asideToggleContainer.classList.toggle("collapsed");
      });
    });
  }

  const resizer = document.querySelector("[data-aside-resizer]");
  const aside = resizer?.closest(".main-container__aside");
  const container = aside?.closest(".main-container");
  if (!resizer || !aside || !container) return;

  const minimumAsideWidth = 300;
  const minimumContentWidth = 320;

  const maximumAsideWidth = () =>
    Math.max(minimumAsideWidth, container.clientWidth - minimumContentWidth);

  const setAsideWidth = (width) => {
    const constrainedWidth = Math.min(
      Math.max(width, minimumAsideWidth),
      maximumAsideWidth(),
    );
    aside.style.width = `${constrainedWidth}px`;
    resizer.setAttribute("aria-valuemin", minimumAsideWidth);
    resizer.setAttribute("aria-valuemax", maximumAsideWidth());
    resizer.setAttribute("aria-valuenow", Math.round(constrainedWidth));
  };

  resizer.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    const startingX = event.clientX;
    const startingWidth = aside.getBoundingClientRect().width;
    resizer.setPointerCapture(event.pointerId);
    aside.classList.add("is-resizing");

    const resize = (moveEvent) => {
      setAsideWidth(startingWidth + startingX - moveEvent.clientX);
    };

    const stopResizing = () => {
      aside.classList.remove("is-resizing");
      resizer.removeEventListener("pointermove", resize);
      resizer.removeEventListener("pointerup", stopResizing);
      resizer.removeEventListener("pointercancel", stopResizing);
    };

    resizer.addEventListener("pointermove", resize);
    resizer.addEventListener("pointerup", stopResizing);
    resizer.addEventListener("pointercancel", stopResizing);
  });

  resizer.addEventListener("keydown", (event) => {
    const currentWidth = aside.getBoundingClientRect().width;
    const step = event.shiftKey ? 50 : 10;
    const widthsByKey = {
      ArrowLeft: currentWidth + step,
      ArrowRight: currentWidth - step,
      Home: minimumAsideWidth,
      End: maximumAsideWidth(),
    };

    if (!(event.key in widthsByKey)) return;
    event.preventDefault();
    setAsideWidth(widthsByKey[event.key]);
  });

  window.addEventListener("resize", () => {
    if (asideToggleContainer?.classList.contains("collapsed")) return;
    setAsideWidth(aside.getBoundingClientRect().width);
  });

  setAsideWidth(aside.getBoundingClientRect().width);
});
