(function () {
  const stage = document.getElementById("cover-stage");
  const preview = document.getElementById("cover-preview");
  const placeholder = document.getElementById("cover-placeholder");
  const fileInput = document.getElementById("cover-file");
  const scaleInput = document.getElementById("cover-scale");
  const xInput = document.getElementById("cover-x");
  const yInput = document.getElementById("cover-y");
  if (!stage || !preview || !xInput || !yInput) return;

  let x = Number(xInput.value) || 50;
  let y = Number(yInput.value) || 50;
  let dragging = false;
  let lastX = 0;
  let lastY = 0;

  function paint() {
    x = Math.min(100, Math.max(0, x));
    y = Math.min(100, Math.max(0, y));
    const scale = scaleInput ? Number(scaleInput.value) || 1 : 1;
    stage.style.setProperty("--x", x + "%");
    stage.style.setProperty("--y", y + "%");
    stage.style.setProperty("--scale", String(scale));
    xInput.value = x.toFixed(1);
    yInput.value = y.toFixed(1);
  }

  stage.addEventListener("pointerdown", function (event) {
    if (preview.hidden) return;
    dragging = true;
    lastX = event.clientX;
    lastY = event.clientY;
    stage.classList.add("is-dragging");
    stage.setPointerCapture(event.pointerId);
  });

  stage.addEventListener("pointermove", function (event) {
    if (!dragging) return;
    const rect = stage.getBoundingClientRect();
    const dx = ((event.clientX - lastX) / rect.width) * 100;
    const dy = ((event.clientY - lastY) / rect.height) * 100;
    x -= dx;
    y -= dy;
    lastX = event.clientX;
    lastY = event.clientY;
    paint();
  });

  function stopDrag() {
    dragging = false;
    stage.classList.remove("is-dragging");
  }

  stage.addEventListener("pointerup", stopDrag);
  stage.addEventListener("pointercancel", stopDrag);
  if (scaleInput) scaleInput.addEventListener("input", paint);

  if (fileInput) {
    fileInput.addEventListener("change", function () {
      const file = fileInput.files && fileInput.files[0];
      if (!file) return;
      preview.src = URL.createObjectURL(file);
      preview.hidden = false;
      if (placeholder) placeholder.hidden = true;
      x = 50;
      y = 50;
      if (scaleInput) scaleInput.value = "1";
      paint();
    });
  }

  paint();
})();
