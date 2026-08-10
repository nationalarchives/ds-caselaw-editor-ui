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

  const updateButtonState = () => {
    const hasChanges = formState(form) !== initialState;

    if (submitButton) {
      submitButton.disabled = !hasChanges;
      submitButton.setAttribute("aria-disabled", String(!hasChanges));
    }

    if (clearButton) {
      clearButton.disabled = !hasChanges;
      clearButton.setAttribute("aria-disabled", String(!hasChanges));
    }
  };

  form.addEventListener("input", updateButtonState);
  form.addEventListener("change", updateButtonState);

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
