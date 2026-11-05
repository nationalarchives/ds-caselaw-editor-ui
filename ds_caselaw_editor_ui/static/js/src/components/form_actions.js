const formState = (form) => {
  const data = new FormData(form);
  data.delete("csrfmiddlewaretoken");
  return Array.from(data.entries()).sort().toString();
};

const initFormActions = (container) => {
  const form = container.closest("form");
  if (!form) return;

  const submitButton = container.querySelector("[data-form-actions-submit]");
  const clearButton = container.querySelector("[data-form-actions-clear]");
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
    setControlEnabled(clearButton, hasChanges);
  };

  form.addEventListener("input", updateButtonState);
  form.addEventListener("change", updateButtonState);
  form.addEventListener("click", updateButtonState);

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      form.reset();
      updateButtonState();
    });
  }

  updateButtonState();
};

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-form-actions]").forEach(initFormActions);
});
