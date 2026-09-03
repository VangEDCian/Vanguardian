(function () {
  const $ = window.jQuery;
  if (!$ || !$.fn.select2) {
    return;
  }

  function readI18n() {
    const node = document.getElementById("dashboard-i18n-data");
    if (!node) {
      return {};
    }
    try {
      return JSON.parse(node.textContent || "{}");
    } catch (error) {
      return {};
    }
  }

  $(function () {
    const labels = readI18n();
    const $siteFilter = $("[data-dashboard-site-filter]");
    const form = document.querySelector("[data-dashboard-filter-form]");
    if ($siteFilter.length === 0 || !form) {
      return;
    }

    $siteFilter.attr("data-placeholder", labels.site_filter_placeholder || "");
    if (labels.site_filter_aria_label) {
      $siteFilter.attr("aria-label", labels.site_filter_aria_label);
    }

    $siteFilter.select2({
      width: "100%",
      allowClear: true,
      placeholder: function () {
        return $(this).data("placeholder") || "";
      },
    });

    $siteFilter.on("change", function () {
      form.submit();
    });
  });
})();
