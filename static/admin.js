// public_resources_map/static/admin.js
document.addEventListener("DOMContentLoaded", () => {
  // ── Leaflet map ──────────────────────────────────────────
  const map = L.map("map").setView([45.75, 21.23], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
              { attribution: "&copy; OpenStreetMap contributors" })
    .addTo(map);

  const markers = new Map();   // id → Leaflet marker
  let currentType = '';   // current filter

  // ── Modal elements ───────────────────────────────────────
  const modal       = document.getElementById("placeModal");
  const form        = document.getElementById("placeForm");
  const idField     = document.getElementById("placeId");
  const nameField   = document.getElementById("name");
  const typeField   = document.getElementById("type");
  const categoryField = document.getElementById("category");
  const cityField   = document.getElementById("city");
  const capacityField = document.getElementById("capacity");
  const descriptionField = document.getElementById("description");
  const contactField = document.getElementById("contact");
  const urlField    = document.getElementById("url");
  const deleteBtn   = document.getElementById("deleteBtn");
  const cancelBtn   = document.getElementById("cancelBtn");
  const typeFilter = document.getElementById("typeFilter");

  let currentLat, currentLon;

  // ── Helpers ──────────────────────────────────────────────
  function loadTypes() {
    fetch("/api/resource-types")
      .then(r => r.json())
      .then(types => {
        types.forEach(type => {
          const option = document.createElement('option');
          option.value = type;
          option.textContent = type;
          typeFilter.appendChild(option);
        });
      });
  }

  function loadMarkers() {
    const url = currentType ? `/admin/api/resources?type=${encodeURIComponent(currentType)}` : "/admin/api/resources";
    fetch(url)
      .then(r => r.json())
      .then(data => {
        // clear existing
        markers.forEach(m => map.removeLayer(m));
        markers.clear();

        data.forEach(p => {
          const m = L.marker([p.lat, p.lon]).addTo(map);
          m.on("click", () => openModal(p));
          markers.set(p.id, m);
        });
      });
  }

  function openModal(place = null) {
    if (place) {                 // editing
      idField.value      = place.id;
      nameField.value    = place.name;
      typeField.value    = place.type;
      categoryField.value = place.category || "";
      cityField.value    = place.city || "";
      capacityField.value = place.capacity || "";
      descriptionField.value = place.description || "";
      contactField.value = place.contact || "";
      urlField.value     = place.url || "";
      currentLat         = place.lat;
      currentLon         = place.lon;
      deleteBtn.classList.remove("hidden");
    } else {                     // creating
      idField.value = "";
      nameField.value = typeField.value = categoryField.value = cityField.value = "";
      capacityField.value = descriptionField.value = contactField.value = urlField.value = "";
      deleteBtn.classList.add("hidden");
    }
    modal.showModal();
  }

  // ── Map click → new place ────────────────────────────────
  map.on("click", e => {
    currentLat = e.latlng.lat;
    currentLon = e.latlng.lng;
    openModal();    // create-mode
  });

  // ── Form submit (create or update) ───────────────────────
  form.addEventListener("submit", e => {
    e.preventDefault();
    const payload = {
      name:        nameField.value,
      type:        typeField.value,
      category:    categoryField.value,
      city:        cityField.value,
      capacity:    capacityField.value ? parseInt(capacityField.value) : null,
      description: descriptionField.value,
      contact:     contactField.value,
      url:         urlField.value,
      lat:         currentLat,
      lon:         currentLon
    };
    const id     = idField.value;
    const method = id ? "PUT" : "POST";
    const url    = id ? `/admin/api/resources/${id}` : "/admin/api/resources";

    fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    .then(r => {
      if (!r.ok) throw new Error("Save failed");
      return r.json();
    })
    .then(() => {
      modal.close();
      loadMarkers();
    })
    .catch(alert);
  });

  // ── Delete ───────────────────────────────────────────────
  deleteBtn.addEventListener("click", () => {
    const id = idField.value;
    if (confirm("Delete this resource?")) {
      fetch(`/admin/api/resources/${id}`, { method: "DELETE" })
        .then(() => { modal.close(); loadMarkers(); });
    }
  });

  cancelBtn.addEventListener("click", () => modal.close());

  // ── Type filter ──────────────────────────────────────
  typeFilter.addEventListener("change", (e) => {
    currentType = e.target.value;
    loadMarkers();
  });

  // initial load
  loadTypes();
  loadMarkers();
});
