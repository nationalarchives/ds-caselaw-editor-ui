const formState = (form) => {
  const data = new FormData(form);
  data.delete("csrfmiddlewaretoken");
  return Array.from(data.entries()).sort().toString();
};

const initFormActions = (container) => {
  const form = container.closest("form");
  if (!form) return;

  const submitButton = container.querySelector("[data-form-actions-submit]");
  const discardButton = container.querySelector("[data-form-actions-discard]");
  const statusMessage =
    form.querySelector("[data-form-actions-status]") ||
    form
      .closest(".aside__content")
      ?.querySelector("[data-form-actions-status]");
  const initialState = formState(form);

  const setControlEnabled = (control, enabled) => {
    if (!control) return;

    if (enabled) {
      control.removeAttribute("disabled");
      control.setAttribute("aria-disabled", "false");
    } else {
      control.setAttribute("disabled", "disabled");
      control.setAttribute("aria-disabled", "true");
    }
  };

  const updateButtonState = () => {
    const hasChanges = formState(form) !== initialState;

    setControlEnabled(submitButton, hasChanges);
    setControlEnabled(discardButton, hasChanges);
    if (statusMessage) {
      statusMessage.setAttribute("aria-hidden", String(!hasChanges));
    }
  };

  form.addEventListener("input", updateButtonState);
  form.addEventListener("change", updateButtonState);
  form.addEventListener("click", updateButtonState);

  if (discardButton) {
    discardButton.addEventListener("click", () => {
      if (!window.confirm("Are you sure you want to discard your changes?")) {
        return;
      }

      form.reset();
      form.dispatchEvent(new Event("form-actions:discard"));
      updateButtonState();
    });
  }

  updateButtonState();
};

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-form-actions]").forEach(initFormActions);
});
