(function () {
  "use strict";

  var MIN_WIDTH = 180;
  var MIN_CONTENT_WIDTH = 420;
  var STEP = 16;
  var STORAGE_KEY = "subjectDetailSidebarWidth";
  var WIDTH_VAR = "--subject-detail-sidebar-width";

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function readStoredWidth() {
    try {
      var value = Number(window.localStorage.getItem(STORAGE_KEY));
      return Number.isFinite(value) ? value : null;
    } catch (error) {
      return null;
    }
  }

  function storeWidth(value) {
    try {
      window.localStorage.setItem(STORAGE_KEY, String(Math.round(value)));
    } catch (error) {
      return;
    }
  }

  function maxWidthForBody(body) {
    return Math.max(MIN_WIDTH, body.clientWidth - MIN_CONTENT_WIDTH);
  }

  function setSidebarWidth(body, resizer, value) {
    var nextWidth = clamp(Math.round(value), MIN_WIDTH, maxWidthForBody(body));
    body.style.setProperty(WIDTH_VAR, nextWidth + "px");
    resizer.setAttribute("aria-valuemin", String(MIN_WIDTH));
    resizer.setAttribute("aria-valuemax", String(maxWidthForBody(body)));
    resizer.setAttribute("aria-valuenow", String(nextWidth));
    return nextWidth;
  }

  function currentWidth(body) {
    var value = window.getComputedStyle(body).getPropertyValue(WIDTH_VAR);
    var parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 240;
  }

  function initSidebarResize() {
    var resizer = document.querySelector("[data-subject-sidebar-resizer]");
    if (!(resizer instanceof HTMLElement)) {
      return;
    }

    var body = resizer.closest(".subject-detail-screen__body");
    if (!(body instanceof HTMLElement)) {
      return;
    }

    var storedWidth = readStoredWidth();
    if (storedWidth !== null) {
      setSidebarWidth(body, resizer, storedWidth);
    } else {
      setSidebarWidth(body, resizer, currentWidth(body));
    }

    resizer.addEventListener("pointerdown", function (event) {
      event.preventDefault();
      body.classList.add("is-resizing");
      resizer.setPointerCapture(event.pointerId);

      function onPointerMove(moveEvent) {
        var bodyRect = body.getBoundingClientRect();
        setSidebarWidth(body, resizer, moveEvent.clientX - bodyRect.left);
      }

      function onPointerUp(upEvent) {
        body.classList.remove("is-resizing");
        resizer.releasePointerCapture(upEvent.pointerId);
        storeWidth(currentWidth(body));
        resizer.removeEventListener("pointermove", onPointerMove);
        resizer.removeEventListener("pointerup", onPointerUp);
        resizer.removeEventListener("pointercancel", onPointerUp);
      }

      resizer.addEventListener("pointermove", onPointerMove);
      resizer.addEventListener("pointerup", onPointerUp);
      resizer.addEventListener("pointercancel", onPointerUp);
    });

    resizer.addEventListener("keydown", function (event) {
      var nextWidth = currentWidth(body);
      if (event.key === "ArrowLeft") {
        nextWidth -= STEP;
      } else if (event.key === "ArrowRight") {
        nextWidth += STEP;
      } else if (event.key === "Home") {
        nextWidth = MIN_WIDTH;
      } else if (event.key === "End") {
        nextWidth = maxWidthForBody(body);
      } else {
        return;
      }

      event.preventDefault();
      storeWidth(setSidebarWidth(body, resizer, nextWidth));
    });

    window.addEventListener("resize", function () {
      setSidebarWidth(body, resizer, currentWidth(body));
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSidebarResize, { once: true });
    return;
  }

  initSidebarResize();
})();
