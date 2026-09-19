(function () {
  document.querySelectorAll("[data-require-for]").forEach(function (requiredBox) {
    requiredBox.addEventListener("change", function () {
      if (!requiredBox.checked) return;
      const key = requiredBox.getAttribute("data-require-for");
      const showBox = document.querySelector('[data-show-for="' + key + '"]');
      if (showBox) showBox.checked = true;
    });
  });
  document.querySelectorAll("[data-show-for]").forEach(function (showBox) {
    showBox.addEventListener("change", function () {
      if (showBox.checked) return;
      const key = showBox.getAttribute("data-show-for");
      const requiredBox = document.querySelector('[data-require-for="' + key + '"]');
      if (requiredBox) requiredBox.checked = false;
    });
  });
})();
