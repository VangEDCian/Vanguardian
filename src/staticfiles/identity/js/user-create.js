document.addEventListener("DOMContentLoaded", () => {
  const $ = window.jQuery;
  const form = document.querySelector("[data-user-create-form]");

  if ($ && $.fn.select2) {
    const studySelect = $(".user-membership-studies-select");
    const siteSelect = $(".user-membership-sites-select");
    const studiesApiUrl = form?.dataset.apiStudiesUrl || "";
    const studySitesApiUrl = form?.dataset.apiStudySitesUrl || "";

    $(".old-select2-single-choice").select2({
      width: "100%",
      placeholder: function () {
        return $(this).data("placeholder") || "";
      }
    });

    $(".old-select2-multiple-choice")
      .not(".user-membership-studies-select, .user-membership-sites-select")
      .select2({
        width: "100%",
        closeOnSelect: false,
        placeholder: function () {
          return $(this).data("placeholder") || "";
        }
      });

    if (studySelect.length > 0) {
      studySelect.select2({
        width: "100%",
        closeOnSelect: false,
        placeholder: function () {
          return $(this).data("placeholder") || "";
        },
        ajax: studiesApiUrl ? {
          url: studiesApiUrl,
          dataType: "json",
          delay: 250,
          data: function (params) {
            return { q: params.term || "" };
          },
          processResults: function (payload) {
            return { results: payload?.results || [] };
          }
        } : undefined
      });
    }

    if (siteSelect.length > 0) {
      siteSelect.select2({
        width: "100%",
        closeOnSelect: false,
        placeholder: function () {
          return $(this).data("placeholder") || "";
        },
        ajax: studySitesApiUrl ? {
          url: studySitesApiUrl,
          dataType: "json",
          delay: 250,
          data: function (params) {
            const selectedStudyIds = studySelect.val() || [];
            return {
              q: params.term || "",
              study_ids: selectedStudyIds.join(",")
            };
          },
          processResults: function (payload) {
            return { results: payload?.results || [] };
          }
        } : undefined
      });
    }

    function syncSiteSelectState() {
      const selectedStudyIds = studySelect.val() || [];
      const hasSelectedStudies = selectedStudyIds.length > 0;

      siteSelect.prop("disabled", !hasSelectedStudies);
      if (!hasSelectedStudies) {
        siteSelect.val(null).trigger("change");
      }
    }

    if (studySelect.length > 0 && siteSelect.length > 0) {
      syncSiteSelectState();
      studySelect.on("change", function () {
        siteSelect.val(null).trigger("change");
        syncSiteSelectState();
      });
    }
  }

  const passwordInputs = document.querySelectorAll(".user-detail-password-input");
  const generateButton = document.querySelector("[data-generate-password]");
  const toggles = document.querySelectorAll("[data-password-toggle]");

  function setPasswordVisibility(input, isVisible) {
    if (!(input instanceof HTMLInputElement)) {
      return;
    }
    input.type = isVisible ? "text" : "password";
  }

  toggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const fieldControl = toggle.closest(".user-detail-password-control");
      const input = fieldControl?.querySelector("input");

      if (!(input instanceof HTMLInputElement)) {
        return;
      }

      setPasswordVisibility(input, input.type === "password");
    });
  });

  function buildGeneratedPassword() {
    const uppercase = "ABCDEFGHJKLMNPQRSTUVWXYZ";
    const lowercase = "abcdefghijkmnopqrstuvwxyz";
    const digits = "23456789";
    const symbols = "!@#$%^&*";
    const alphabet = `${uppercase}${lowercase}${digits}${symbols}`;
    const passwordLength = 16;
    const requiredChars = [uppercase, lowercase, digits, symbols].map(
      (charset) => charset[randomIndex(charset.length)]
    );
    const passwordChars = [...requiredChars];

    while (passwordChars.length < passwordLength) {
      passwordChars.push(alphabet[randomIndex(alphabet.length)]);
    }

    for (let index = passwordChars.length - 1; index > 0; index -= 1) {
      const swapIndex = randomIndex(index + 1);
      [passwordChars[index], passwordChars[swapIndex]] = [passwordChars[swapIndex], passwordChars[index]];
    }

    return passwordChars.join("");
  }

  function randomIndex(max) {
    if (window.crypto?.getRandomValues) {
      const randomValues = new Uint32Array(1);
      window.crypto.getRandomValues(randomValues);
      return randomValues[0] % max;
    }

    return Math.floor(Math.random() * max);
  }

  if (generateButton) {
    generateButton.addEventListener("click", () => {
      const generatedPassword = buildGeneratedPassword();

      passwordInputs.forEach((input) => {
        if (!(input instanceof HTMLInputElement)) {
          return;
        }
        input.value = generatedPassword;
        setPasswordVisibility(input, true);
      });
    });
  }
});
