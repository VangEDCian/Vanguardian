(function () {
  if (window.VanguardianCommonFlatpickrInit) {
    return;
  }

  function readBool(node, key, defaultValue) {
    const value = node.dataset[key];
    if (value === undefined) {
      return defaultValue;
    }
    return !["0", "false", "False", ""].includes(value);
  }

  function readInt(node, key, defaultValue) {
    const value = node.dataset[key];
    if (value === undefined || value === "") {
      return defaultValue;
    }
    const parsed = parseInt(value, 10);
    return Number.isNaN(parsed) ? defaultValue : parsed;
  }

  function buildOptions(input) {
    const kind = input.dataset.flatpickrKind;
    const isReadonly = input.hasAttribute("readonly");
    const isDisabled = input.hasAttribute("disabled");
    const options = {
      disableMobile: true,
      allowInput: !isReadonly && !isDisabled && readBool(input, "flatpickrAllowInput", true),
      clickOpens: !isReadonly && !isDisabled,
      time_24hr: true,
    };

    if (input.dataset.flatpickrMinDate) {
      options.minDate = input.dataset.flatpickrMinDate;
    }
    if (input.dataset.flatpickrMaxDate) {
      options.maxDate = input.dataset.flatpickrMaxDate;
    }

    if (kind === "time") {
      options.enableTime = true;
      options.noCalendar = true;
      options.dateFormat = input.dataset.flatpickrDateFormat || "H:i";
      options.minuteIncrement = readInt(input, "flatpickrMinuteIncrement", 1);
      return options;
    }

    if (kind === "datetime") {
      options.enableTime = true;
      options.noCalendar = false;
      options.dateFormat = input.dataset.flatpickrDateFormat || "Y-m-d H:i";
      options.minuteIncrement = readInt(input, "flatpickrMinuteIncrement", 1);
      return options;
    }

    options.enableTime = false;
    options.noCalendar = false;
    options.dateFormat = input.dataset.flatpickrDateFormat || "Y-m-d";
    return options;
  }

  function initialize(root) {
    if (!window.flatpickr) {
      return;
    }

    const scope = root || document;
    scope.querySelectorAll("[data-flatpickr-kind]").forEach(function (input) {
      if (input.dataset.flatpickrBound === "1") {
        return;
      }

      window.flatpickr(input, buildOptions(input));
      input.dataset.flatpickrBound = "1";
    });

    scope.querySelectorAll("[data-flatpickr-open]").forEach(function (button) {
      if (button.dataset.flatpickrBound === "1") {
        return;
      }

      button.addEventListener("click", function () {
        const targetId = button.dataset.flatpickrTarget;
        if (!targetId) {
          return;
        }

        const input = document.getElementById(targetId);
        if (!input || !input._flatpickr || input.disabled || input.hasAttribute("readonly")) {
          return;
        }

        input._flatpickr.open();
      });

      button.dataset.flatpickrBound = "1";
    });
  }

  window.VanguardianCommonFlatpickrInit = initialize;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      initialize(document);
    });
  } else {
    initialize(document);
  }
})();
