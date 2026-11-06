const NEW_INPUT_INDEX_PLACEHOLDER = "__INDEX__";

const replaceIndexPlaceholder = (entry, index) => {
  entry.querySelectorAll("[id]").forEach((node) => {
    node.id = node.id.replaceAll(NEW_INPUT_INDEX_PLACEHOLDER, String(index));
  });
  entry.querySelectorAll("[for]").forEach((node) => {
    const labelFor = node.getAttribute("for");
    if (labelFor) {
      node.setAttribute(
        "for",
        labelFor.replaceAll(NEW_INPUT_INDEX_PLACEHOLDER, String(index)),
      );
    }
  });
};

const newClaimInputName = (form) => form.dataset.newClaimInputName;

const formEntriesKey = (form) => {
  const data = new FormData(form);
  data.delete("csrfmiddlewaretoken");
  return Array.from(data.entries()).sort().toString();
};

const setControlDisabled = (control, disabled) => {
  control.toggleAttribute("disabled", disabled);
  control.setAttribute("aria-disabled", String(disabled));
};

const initMetadataCompactForm = (form) => {
  if (!form.dataset.newClaimInputName) return;

  const claimList = form.querySelector("[data-metadata-compact-list]");
  const addRow = form.querySelector("[data-metadata-compact-add-row]");
  const addButton = form.querySelector("[data-metadata-compact-add]");
  const newEntryTemplate = form.querySelector(
    "[data-metadata-compact-new-template]",
  );
  if (!claimList || !addRow || !addButton || !newEntryTemplate) return;

  const startedWithoutPersistedJudges = !form.querySelector(
    ".aside__metadata-compact-remove-input",
  );
  let nextInputIndex = form.querySelectorAll(
    "[data-metadata-compact-new-entry]",
  ).length;

  const isDocumentEditForm = form.matches("[data-document-edit-form]");
  const documentEditForm = document.querySelector("[data-document-edit-form]");
  const documentEditFormInitialState =
    !isDocumentEditForm && documentEditForm && documentEditForm !== form
      ? formEntriesKey(documentEditForm)
      : null;

  const syncNewInputName = (input) => {
    if (input.value.trim()) {
      input.name = newClaimInputName(form);
    } else {
      input.removeAttribute("name");
    }
  };

  const updateRemoveControls = () => {
    const persistedRemoveInputs = Array.from(
      form.querySelectorAll(".aside__metadata-compact-remove-input"),
    );
    const newEntries = Array.from(
      form.querySelectorAll("[data-metadata-compact-new-entry]"),
    );
    const activePersistedCount = persistedRemoveInputs.filter(
      (input) => !input.checked,
    ).length;
    const activeNewCount = newEntries.filter((entry) =>
      entry.querySelector("[data-metadata-compact-new-input]")?.value.trim(),
    ).length;
    const activeJudgeCount = activePersistedCount + activeNewCount;

    persistedRemoveInputs.forEach((input) => {
      const disabled = !input.checked && activeJudgeCount <= 1;
      const label = input
        .closest(".aside__metadata-compact-entry")
        ?.querySelector(".aside__metadata-compact-remove-label");
      setControlDisabled(input, disabled);
      if (label) {
        label.setAttribute("aria-disabled", String(disabled));
        label.toggleAttribute("title", disabled);
        if (disabled) label.title = "At least one judge is required";
      }
    });

    newEntries.forEach((entry, index) => {
      const input = entry.querySelector("[data-metadata-compact-new-input]");
      const removeButton = entry.querySelector(
        "[data-metadata-compact-remove-new]",
      );
      if (!input || !removeButton) return;

      input.required =
        activePersistedCount === 0 && activeNewCount === 0 && index === 0;

      const hasValue = Boolean(input.value.trim());
      const disabled = hasValue
        ? activeJudgeCount <= 1
        : activeJudgeCount === 0 && newEntries.length <= 1;
      setControlDisabled(removeButton, disabled);
      removeButton.toggleAttribute("title", disabled);
      if (disabled) removeButton.title = "At least one judge is required";
    });
  };

  const wireNewEntry = (entry) => {
    const input = entry.querySelector("[data-metadata-compact-new-input]");
    const removeButton = entry.querySelector(
      "[data-metadata-compact-remove-new]",
    );
    if (!input || !removeButton) return;

    input.addEventListener("input", () => {
      syncNewInputName(input);
      updateRemoveControls();
    });

    removeButton.addEventListener("click", () => {
      entry.remove();
      if (
        startedWithoutPersistedJudges &&
        !form.querySelector("[data-metadata-compact-initial-new-entry]")
      ) {
        const firstRemainingEntry = form.querySelector(
          "[data-metadata-compact-new-entry]",
        );
        if (firstRemainingEntry) {
          firstRemainingEntry.dataset.metadataCompactInitialNewEntry = "";
        }
      }
      updateRemoveControls();
      form.dispatchEvent(new Event("input", { bubbles: true }));
    });
  };

  form
    .querySelectorAll("[data-metadata-compact-new-entry]")
    .forEach(wireNewEntry);
  form
    .querySelectorAll(".aside__metadata-compact-remove-input")
    .forEach((input) => input.addEventListener("change", updateRemoveControls));

  addButton.addEventListener("click", () => {
    const entry = newEntryTemplate.content
      .querySelector("[data-metadata-compact-new-entry]")
      ?.cloneNode(true);
    if (!entry) return;

    replaceIndexPlaceholder(entry, nextInputIndex);
    nextInputIndex += 1;
    claimList.insertBefore(entry, addRow);
    wireNewEntry(entry);
    updateRemoveControls();
    entry.querySelector("[data-metadata-compact-new-input]")?.focus();
  });

  form.addEventListener("submit", (event) => {
    form
      .querySelectorAll("[data-metadata-compact-new-input]")
      .forEach(syncNewInputName);

    if (
      !isDocumentEditForm &&
      documentEditForm &&
      documentEditForm !== form &&
      documentEditFormInitialState !== null &&
      formEntriesKey(documentEditForm) !== documentEditFormInitialState &&
      !window.confirm(
        "You have unsaved changes. To save them, select Cancel and click the Save button. Continue without saving?",
      )
    ) {
      event.preventDefault();
    }
  });

  const clearButton = form.querySelector("[data-form-actions-clear]");
  if (clearButton) {
    clearButton.addEventListener("click", () => {
      form
        .querySelectorAll(
          "[data-metadata-compact-new-entry]:not([data-metadata-compact-initial-new-entry])",
        )
        .forEach((entry) => entry.remove());
      form
        .querySelectorAll("[data-metadata-compact-new-input]")
        .forEach(syncNewInputName);
      nextInputIndex = form.querySelectorAll(
        "[data-metadata-compact-new-entry]",
      ).length;
      updateRemoveControls();
      form.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }

  updateRemoveControls();
};

document.addEventListener("DOMContentLoaded", () => {
  document
    .querySelectorAll("[data-metadata-compact-form]")
    .forEach(initMetadataCompactForm);
});
