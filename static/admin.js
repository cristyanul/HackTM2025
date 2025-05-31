// public_resources_map/static/admin.js
document.addEventListener("DOMContentLoaded", () => {
  // ── Leaflet map ──────────────────────────────────────────
  const map = L.map("map").setView([45.75, 21.23], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
              { attribution: "&copy; OpenStreetMap contributors" })
    .addTo(map);

  const markers = new Map();   // id → Leaflet marker

  // ── Modal elements ───────────────────────────────────────
  const modal       = document.getElementById("placeModal");
  const form        = document.getElementById("placeForm");
  const idField     = document.getElementById("placeId");
  const nameField   = document.getElementById("name");
  const typeField   = document.getElementById("type");
  const categoryField = document.getElementById("category");
  const cityField   = document.getElementById("city");
  const urlField    = document.getElementById("url");
  const deleteBtn   = document.getElementById("deleteBtn");
  const cancelBtn   = document.getElementById("cancelBtn");

  let currentLat, currentLon;

  // ── Helpers ──────────────────────────────────────────────
  function loadMarkers() {
    fetch("/admin/api/places")
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
      urlField.value     = place.url || "";
      currentLat         = place.lat;
      currentLon         = place.lon;
      deleteBtn.classList.remove("hidden");
    } else {                     // creating
      idField.value = "";
      nameField.value = typeField.value = categoryField.value = cityField.value = urlField.value = "";
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
      name:     nameField.value,
      type:     typeField.value,
      category: categoryField.value,
      city:     cityField.value,
      url:      urlField.value,
      lat:      currentLat,
      lon:      currentLon
    };
    const id     = idField.value;
    const method = id ? "PUT" : "POST";
    const url    = id ? `/admin/api/places/${id}` : "/admin/api/places";

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
    if (confirm("Delete this place?")) {
      fetch(`/admin/api/places/${id}`, { method: "DELETE" })
        .then(() => { modal.close(); loadMarkers(); });
    }
  });

  cancelBtn.addEventListener("click", () => modal.close());

  // initial load
  loadMarkers();
});
