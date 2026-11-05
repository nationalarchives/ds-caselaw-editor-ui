const PENDING_INDEX_PLACEHOLDER = "__INDEX__";
const PENDING_VALUE_PLACEHOLDER = "__VALUE__";

const uniquifyEntryIds = (entry, suffix) => {
  const idMap = new Map();
  entry.querySelectorAll("[id]").forEach((node) => {
    const nextId = `${node.id}-pending-${suffix}`;
    idMap.set(node.id, nextId);
    node.id = nextId;
  });
  entry.querySelectorAll("[for]").forEach((node) => {
    const currentFor = node.getAttribute("for");
    if (currentFor && idMap.has(currentFor)) {
      node.setAttribute("for", idMap.get(currentFor));
    }
  });
};

const replaceIndexPlaceholder = (entry, index) => {
  entry.querySelectorAll("[id]").forEach((node) => {
    node.id = node.id.replaceAll(PENDING_INDEX_PLACEHOLDER, String(index));
  });
  entry.querySelectorAll("[for]").forEach((node) => {
    const labelFor = node.getAttribute("for");
    if (labelFor) {
      node.setAttribute(
        "for",
        labelFor.replaceAll(PENDING_INDEX_PLACEHOLDER, String(index)),
      );
    }
  });
};

const setRemoveLabel = (entry, value) => {
  const label = entry.querySelector(".govuk-checkboxes__label");
  if (label) {
    label.textContent = `Remove ${value}`;
  }
};

const newClaimInputName = (form) => form.dataset.newClaimInputName;

const formEntriesKey = (form) => {
  const data = new FormData(form);
  data.delete("csrfmiddlewaretoken");
  return Array.from(data.entries()).sort().toString();
};

const wirePendingRemove = (form, entry) => {
  const claimInputName = newClaimInputName(form);
  const checkbox = entry.querySelector('input[type="checkbox"]');
  const hidden = entry.querySelector(`input[name="${claimInputName}"]`);
  if (!checkbox || !hidden) {
    return;
  }

  checkbox.addEventListener("change", () => {
    hidden.disabled = checkbox.checked;
    form.dispatchEvent(new Event("input", { bubbles: true }));
  });
};

const preparePendingEntry = (form, entry, index, value) => {
  entry.dataset.metadataCompactPending = "";
  entry.querySelector(".aside__metadata-compact-entry__name").textContent =
    value;
  setRemoveLabel(entry, value);

  entry
    .querySelectorAll('input[type="hidden"]')
    .forEach((node) => node.remove());

  const hidden = document.createElement("input");
  hidden.type = "hidden";
  hidden.name = newClaimInputName(form);
  hidden.value = value;
  entry.appendChild(hidden);

  const checkbox = entry.querySelector('input[type="checkbox"]');
  if (checkbox) {
    checkbox.checked = false;
    checkbox.removeAttribute("name");
    checkbox.value = "remove";
    uniquifyEntryIds(entry, index);
  }

  wirePendingRemove(form, entry);
  return entry;
};

const createPendingEntry = (form, claimList, template, index, value) => {
  const prototype = claimList.querySelector(
    ".aside__metadata-compact-entry:not([data-metadata-compact-pending])",
  );

  let entry = null;
  if (prototype) {
    entry = prototype.cloneNode(true);
  } else {
    entry = template.content
      .querySelector(".aside__metadata-compact-entry")
      ?.cloneNode(true);
    if (entry) {
      replaceIndexPlaceholder(entry, index);
    }
  }

  if (!entry) {
    return null;
  }

  return preparePendingEntry(form, entry, index, value);
};

const clearPendingEntries = (form) => {
  form
    .querySelectorAll("[data-metadata-compact-pending]")
    .forEach((entry) => entry.remove());
};

const initMetadataCompactForm = (form) => {
  if (!form.dataset.newClaimInputName) {
    return;
  }

  const claimList = form.querySelector("[data-metadata-compact-list]");
  const addRow = form.querySelector("[data-metadata-compact-add-row]");
  const addButton = form.querySelector("[data-metadata-compact-add]");
  const draftInput = form.querySelector("[data-metadata-compact-draft]");
  const pendingTemplate = form.querySelector(
    "[data-metadata-compact-pending-template]",
  );
  if (!claimList || !addRow || !addButton || !draftInput || !pendingTemplate) {
    return;
  }

  let pendingIndex = 0;

  const documentEditForm = document.querySelector("[data-document-edit-form]");
  const documentEditFormInitialState = documentEditForm
    ? formEntriesKey(documentEditForm)
    : null;

  const addPendingValue = () => {
    const value = draftInput.value.trim();
    if (!value) {
      return;
    }

    const entry = createPendingEntry(
      form,
      claimList,
      pendingTemplate,
      pendingIndex,
      value,
    );
    if (!entry) {
      return;
    }

    pendingIndex += 1;
    claimList.insertBefore(entry, addRow);
    draftInput.value = "";
    draftInput.focus();
    form.dispatchEvent(new Event("input", { bubbles: true }));
  };

  addButton.addEventListener("click", addPendingValue);

  draftInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addPendingValue();
    }
  });

  form.addEventListener("submit", (event) => {
    if (draftInput.value.trim()) {
      addPendingValue();
    }

    if (
      documentEditForm &&
      documentEditFormInitialState !== null &&
      formEntriesKey(documentEditForm) !== documentEditFormInitialState &&
      !window.confirm(
        "You have unsaved changes in the judgment form. Updating judges will reload the page and those edits will be lost. Continue?",
      )
    ) {
      event.preventDefault();
    }
  });

  const clearButton = form.querySelector("[data-form-actions-clear]");
  if (clearButton) {
    clearButton.addEventListener("click", () => {
      clearPendingEntries(form);
      pendingIndex = 0;
      draftInput.value = "";
      form.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }
};

document.addEventListener("DOMContentLoaded", () => {
  document
    .querySelectorAll("[data-metadata-compact-form]")
    .forEach(initMetadataCompactForm);
});
