document.querySelectorAll("[data-address-fields]").forEach(function (root) {
  var countrySelect = root.querySelector(".country-select");
  var stateSelect = root.querySelector(".state-select");
  var stateFree = root.querySelector(".state-free");
  var postalInput = root.querySelector(".postal-input");
  var postalList = root.querySelector(".postal-list");
  var postalHint = root.querySelector(".postal-hint");
  var listId = "postal-" + Math.random().toString(36).slice(2, 8);
  postalList.id = listId;
  postalInput.setAttribute("list", listId);

  var prefixes = {};
  var examples = [];

  function setHint() {
    var parts = [];
    if (examples.length) parts.push("Examples for this country: " + examples.join(", "));
    var prefix = prefixes[stateSelect.value];
    if (prefix && !stateSelect.disabled) {
      parts.push("In this state or province they often start with " + prefix + ".");
    }
    postalHint.textContent = parts.join(" ");
  }

  function useStateList(states) {
    stateSelect.hidden = false;
    stateSelect.disabled = false;
    stateSelect.required = true;
    stateFree.hidden = true;
    stateFree.disabled = true;
    stateSelect.innerHTML = '<option value="">Select a state or province</option>';
    states.forEach(function (state) {
      var option = document.createElement("option");
      option.value = state.code;
      option.textContent = state.name;
      stateSelect.appendChild(option);
    });
    if (root.dataset.selectedState) stateSelect.value = root.dataset.selectedState;
  }

  function useFreeState() {
    stateSelect.hidden = true;
    stateSelect.disabled = true;
    stateSelect.required = false;
    stateFree.hidden = false;
    stateFree.disabled = false;
  }

  function loadCountry(code) {
    prefixes = {};
    examples = [];
    postalList.innerHTML = "";
    setHint();
    if (!code) {
      stateSelect.disabled = true;
      stateSelect.required = false;
      stateSelect.innerHTML = '<option value="">Select a country first</option>';
      return;
    }
    fetch(root.dataset.detailBase.replace("XX", code), { headers: { Accept: "application/json" } })
      .then(function (response) { return response.json(); })
      .then(function (detail) {
        examples = detail.postal_examples || [];
        prefixes = detail.postal_prefixes || {};
        examples.forEach(function (example) {
          var option = document.createElement("option");
          option.value = example;
          postalList.appendChild(option);
        });
        if (detail.states && detail.states.length) useStateList(detail.states);
        else useFreeState();
        setHint();
      })
      .catch(function () {
        postalHint.textContent = "Regions could not be loaded. Try another country.";
      });
  }

  countrySelect.addEventListener("change", function () {
    root.dataset.selectedState = "";
    loadCountry(countrySelect.value);
  });
  stateSelect.addEventListener("change", setHint);

  fetch(root.dataset.countriesUrl, { headers: { Accept: "application/json" } })
    .then(function (response) { return response.json(); })
    .then(function (rows) {
      countrySelect.innerHTML = '<option value="">Select a country</option>';
      (rows || []).forEach(function (country) {
        var option = document.createElement("option");
        option.value = country.code;
        option.textContent = country.name;
        countrySelect.appendChild(option);
      });
      if (root.dataset.selectedCountry) {
        countrySelect.value = root.dataset.selectedCountry;
        loadCountry(countrySelect.value);
      }
    })
    .catch(function () {
      countrySelect.innerHTML = '<option value="">Countries are unavailable</option>';
    });
});

var addressPicker = document.getElementById("address-id");
var newAddress = document.getElementById("new-address");
var tenantPicker = document.querySelector("[name=tenant_id]");

function syncAddressMode() {
  if (!newAddress) return;
  var adding = !addressPicker || addressPicker.value === "";
  newAddress.hidden = !adding;
  newAddress.querySelectorAll("input, select").forEach(function (field) {
    if (!adding) {
      if (field.required) field.dataset.wasRequired = "1";
      field.required = false;
    } else if (field.dataset.wasRequired === "1") {
      field.required = true;
    }
  });
}

function filterSavedAddresses() {
  if (!addressPicker) return;
  var tenant = tenantPicker ? tenantPicker.value : "";
  var visible = 0;
  addressPicker.querySelectorAll("option[data-tenant]").forEach(function (option) {
    var show = !tenant || option.dataset.tenant === tenant;
    option.hidden = !show;
    option.disabled = !show;
    if (show) visible += 1;
  });
  if (addressPicker.selectedOptions[0] && addressPicker.selectedOptions[0].disabled) {
    addressPicker.value = "";
  }
  var label = document.getElementById("saved-address");
  if (label) label.hidden = visible === 0;
  syncAddressMode();
}

if (addressPicker) {
  addressPicker.addEventListener("change", syncAddressMode);
  if (tenantPicker) tenantPicker.addEventListener("change", filterSavedAddresses);
  filterSavedAddresses();
}
