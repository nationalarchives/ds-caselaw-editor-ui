function replaceFormIndex(html, index) {
  return html.split("__prefix__").join(index);
}

function updateElementIndex(element, prefix, index) {
  ["for", "id", "name"].forEach((attribute) => {
    const value = element.getAttribute(attribute);

    if (value) {
      element.setAttribute(
        attribute,
        value.replace(
          new RegExp(`${prefix}-\\d+-`, "g"),
          `${prefix}-${index}-`,
        ),
      );
    }
  });
}

function reindexForms(formset, prefix, totalForms) {
  formset.querySelectorAll("[data-formset-form]").forEach((form, index) => {
    form
      .querySelectorAll("[for], [id], [name]")
      .forEach((element) => updateElementIndex(element, prefix, index));
  });

  totalForms.value = formset.querySelectorAll("[data-formset-form]").length;
}

function getField(form, name) {
  return form.querySelector(`[name$="-${name}"]`);
}

function getIdentifierTypeLabel(form) {
  const typeSelect = getField(form, "type");

  if (typeSelect && typeSelect.tagName === "SELECT") {
    if (!typeSelect.value) {
      return "";
    }

    return typeSelect.selectedOptions[0]?.textContent.trim() || "";
  }

  return (
    form.querySelector("[data-formset-type-label]")?.dataset.formsetTypeLabel ||
    ""
  );
}

function getIdentifierTypeValue(form) {
  return getField(form, "type")?.value || "";
}

function getIdentifierValue(form) {
  return getField(form, "value")?.value.trim() || "";
}

function isDeprecated(form) {
  return getField(form, "deprecated")?.checked || false;
}

function isDeleted(form) {
  return getField(form, "DELETE")?.checked || false;
}

function isExisting(form) {
  return form.dataset.formsetExisting === "true";
}

function isBlankNewForm(form) {
  return (
    !isExisting(form) &&
    !getIdentifierTypeValue(form) &&
    !getIdentifierValue(form) &&
    !isDeprecated(form)
  );
}

function hideForms(formset) {
  formset.querySelectorAll("[data-formset-form]").forEach((form) => {
    form.hidden = true;
    form.classList.remove("formset__form--active");
  });
}

function showForm(formset, form) {
  hideForms(formset);
  form.hidden = false;
  form.classList.add("formset__form--active");
}

function buildTag(form, index) {
  const tag = document.createElement("button");
  tag.type = "button";
  tag.className = "formset__tag";
  tag.dataset.formsetTagIndex = index;

  const label = document.createElement("span");
  const deprecatedLabel = isDeprecated(form) ? " (Deprecated)" : "";
  label.textContent = `${getIdentifierTypeLabel(form)}: ${getIdentifierValue(form)}${deprecatedLabel}`;

  const remove = document.createElement("span");
  remove.className = "formset__tag-remove";
  remove.setAttribute("aria-hidden", "true");
  remove.textContent = "×";

  tag.append(label, remove);
  return tag;
}

function renderTags(formset) {
  const tagsContainer = formset.querySelector("[data-formset-tags]");
  tagsContainer.innerHTML = "";

  formset.querySelectorAll("[data-formset-form]").forEach((form, index) => {
    if (isDeleted(form) || isBlankNewForm(form)) {
      return;
    }

    if (!getIdentifierTypeLabel(form) || !getIdentifierValue(form)) {
      return;
    }

    tagsContainer.appendChild(buildTag(form, index));
  });
}

function addForm(formset, emptyFormTemplate, formsContainer, totalForms) {
  const nextIndex = parseInt(totalForms.value, 10);
  const wrapper = document.createElement("div");
  wrapper.innerHTML = replaceFormIndex(
    emptyFormTemplate.innerHTML,
    nextIndex,
  ).trim();

  const form = wrapper.firstElementChild;
  formsContainer.appendChild(form);
  totalForms.value = nextIndex + 1;
  showForm(formset, form);
}

function removeForm(formset, prefix, totalForms, form) {
  form.remove();
  reindexForms(formset, prefix, totalForms);
  renderTags(formset);
}

function deleteExistingForm(formset, form) {
  const deleteField = getField(form, "DELETE");

  if (deleteField) {
    deleteField.checked = true;
  }

  hideForms(formset);
  renderTags(formset);
}

function initFormset(formset) {
  const prefix = formset.dataset.formsetPrefix;
  const totalForms = formset.querySelector(`#id_${prefix}-TOTAL_FORMS`);
  const emptyFormTemplate = formset.querySelector("[data-formset-empty-form]");
  const formsContainer = formset.querySelector("[data-formset-forms]");
  const addButton = formset.querySelector("[data-formset-add]");

  if (
    !prefix ||
    !totalForms ||
    !emptyFormTemplate ||
    !formsContainer ||
    !addButton
  ) {
    return;
  }

  renderTags(formset);

  addButton.addEventListener("click", () => {
    addForm(formset, emptyFormTemplate, formsContainer, totalForms);
  });

  formset.addEventListener("click", (event) => {
    const tagRemove = event.target.closest(".formset__tag-remove");
    const tag = event.target.closest("[data-formset-tag-index]");
    const removeButton = event.target.closest("[data-formset-remove]");
    const applyButton = event.target.closest("[data-formset-apply]");

    if (tagRemove && tag) {
      const form = formset.querySelectorAll("[data-formset-form]")[
        tag.dataset.formsetTagIndex
      ];

      if (isExisting(form)) {
        deleteExistingForm(formset, form);
      } else {
        removeForm(formset, prefix, totalForms, form);
      }

      return;
    }

    if (tag) {
      const form = formset.querySelectorAll("[data-formset-form]")[
        tag.dataset.formsetTagIndex
      ];
      showForm(formset, form);
      return;
    }

    if (removeButton) {
      removeForm(
        formset,
        prefix,
        totalForms,
        removeButton.closest("[data-formset-form]"),
      );
      return;
    }

    if (applyButton) {
      const form = applyButton.closest("[data-formset-form]");

      if (!getIdentifierTypeValue(form) || !getIdentifierValue(form)) {
        renderTags(formset);
        return;
      }

      hideForms(formset);
      renderTags(formset);
    }
  });
}

document.querySelectorAll("[data-formset-prefix]").forEach(initFormset);
