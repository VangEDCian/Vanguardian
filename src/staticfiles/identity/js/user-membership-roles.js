(function () {
  function readJsonScript(id, fallback) {
    const node = document.getElementById(id);
    if (!node) {
      return fallback;
    }
    try {
      return JSON.parse(node.textContent || "");
    } catch (_) {
      return fallback;
    }
  }

  function optionData(option) {
    if (!option) {
      return {};
    }
    return {
      id: String(option.value || option.id || "").trim(),
      text: String(option.text || option.label || "").trim(),
      studyId: String(option.dataset?.studyId || option.study_id || option.studyId || "").trim(),
    };
  }

  function selectedItems(select, $select) {
    const fromDom = Array.from(select.selectedOptions || [])
      .map(optionData)
      .filter((item) => item.id);
    const $ = window.jQuery;
    const hasSelect2Instance =
      $select?.length > 0 &&
      ($select.data("select2") || select.classList.contains("select2-hidden-accessible"));

    if (!$ || !$.fn.select2 || !hasSelect2Instance) {
      return fromDom;
    }
    const byId = new Map(fromDom.map((item) => [item.id, item]));
    let select2Items = [];
    try {
      select2Items = $select.select2("data") || [];
    } catch (_) {
      return fromDom;
    }
    select2Items.forEach((item) => {
      const normalized = {
        id: String(item.id || "").trim(),
        text: String(item.text || "").trim(),
        studyId: String(item.study_id || item.studyId || byId.get(String(item.id || ""))?.studyId || "").trim(),
      };
      if (normalized.id) {
        byId.set(normalized.id, normalized);
      }
    });
    return Array.from(byId.values()).filter((item) => item.id);
  }

  function currentRoleMap(container) {
    const out = {};
    container.querySelectorAll("[data-membership-role-select]").forEach((select) => {
      if (!(select instanceof HTMLSelectElement)) {
        return;
      }
      const scopeId = String(select.dataset.scopeId || "").trim();
      const roleId = String(select.value || "").trim();
      if (scopeId && roleId) {
        out[scopeId] = roleId;
      }
    });
    return out;
  }

  function roleOptionsForStudy(roleOptions, studyId) {
    return roleOptions.filter((role) => String(role.study_id || role.studyId || "").trim() === String(studyId || "").trim());
  }

  function buildRoleSelect({ name, scopeId, selectedRoleId, roleOptions, disabled }) {
    const select = document.createElement("select");
    select.name = name;
    select.className = "old-select2-single-choice user-membership-role-select";
    select.dataset.membershipRoleSelect = "";
    select.dataset.scopeId = scopeId;
    select.dataset.placeholder = "Select role";
    if (disabled) {
      select.disabled = true;
    }

    const empty = document.createElement("option");
    empty.value = "";
    select.appendChild(empty);

    roleOptions.forEach((role) => {
      const option = document.createElement("option");
      option.value = String(role.value || "");
      option.textContent = String(role.label || "");
      if (String(role.value || "") === String(selectedRoleId || "")) {
        option.selected = true;
      }
      select.appendChild(option);
    });
    return select;
  }

  function renderRows({ container, items, roleOptions, selectedMap, fieldName, canManage }) {
    const preservedMap = currentRoleMap(container);
    container.replaceChildren();
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "user-membership-role-list__empty";
      empty.textContent = "Select a scope to assign a role.";
      container.appendChild(empty);
      return;
    }

    items.forEach((item) => {
      const row = document.createElement("div");
      row.className = "user-membership-role-row";
      row.dataset.scopeId = item.id;

      const label = document.createElement("div");
      label.className = "user-membership-role-row__label";
      label.textContent = item.text || item.id;
      row.appendChild(label);

      const control = document.createElement("div");
      control.className = "user-membership-role-row__control";
      const selectedRoleId = preservedMap[item.id] || selectedMap[item.id] || "";
      control.appendChild(
        buildRoleSelect({
          name: `${fieldName}[${item.id}]`,
          scopeId: item.id,
          selectedRoleId,
          roleOptions: roleOptionsForStudy(roleOptions, item.studyId || item.id),
          disabled: !canManage,
        }),
      );
      row.appendChild(control);
      container.appendChild(row);
    });

    const $ = window.jQuery;
    if ($ && $.fn.select2) {
      $(container)
        .find(".old-select2-single-choice")
        .select2({
          width: "100%",
          placeholder: function () {
            return $(this).data("placeholder") || "";
          },
        });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector("[data-user-create-form], [data-user-detail-form]");
    const studySelect = document.querySelector(".user-membership-studies-select");
    const siteSelect = document.querySelector(".user-membership-sites-select");
    const studyContainer = document.querySelector("[data-study-membership-role-container]");
    const siteContainer = document.querySelector("[data-site-membership-role-container]");
    if (!form || !studySelect || !siteSelect || !studyContainer || !siteContainer) {
      return;
    }

    const $ = window.jQuery;
    const $studySelect = $ ? $(studySelect) : null;
    const $siteSelect = $ ? $(siteSelect) : null;
    const canManage = form.dataset.canManagePermissions ? form.dataset.canManagePermissions === "true" : true;
    const studyRoleOptions = readJsonScript("study-membership-role-options-data", []);
    const siteRoleOptions = readJsonScript("site-membership-role-options-data", []);
    const selectedStudyRoleMap = readJsonScript("selected-study-role-map-data", {});
    const selectedSiteRoleMap = readJsonScript("selected-site-role-map-data", {});

    function renderStudyRoles() {
      const studies = selectedItems(studySelect, $studySelect).map((item) => ({
        ...item,
        studyId: item.id,
      }));
      renderRows({
        container: studyContainer,
        items: studies,
        roleOptions: studyRoleOptions,
        selectedMap: selectedStudyRoleMap,
        fieldName: "study_roles",
        canManage,
      });
    }

    function renderSiteRoles() {
      renderRows({
        container: siteContainer,
        items: selectedItems(siteSelect, $siteSelect),
        roleOptions: siteRoleOptions,
        selectedMap: selectedSiteRoleMap,
        fieldName: "site_roles",
        canManage,
      });
    }

    renderStudyRoles();
    renderSiteRoles();

    if ($studySelect) {
      $studySelect.on("change", function () {
        renderStudyRoles();
        renderSiteRoles();
      });
    } else {
      studySelect.addEventListener("change", function () {
        renderStudyRoles();
        renderSiteRoles();
      });
    }

    if ($siteSelect) {
      $siteSelect.on("change", renderSiteRoles);
    } else {
      siteSelect.addEventListener("change", renderSiteRoles);
    }

    form.addEventListener("reset", function () {
      window.setTimeout(function () {
        renderStudyRoles();
        renderSiteRoles();
      }, 0);
    });
  });
})();
