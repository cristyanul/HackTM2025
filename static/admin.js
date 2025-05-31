// public_resources_map/static/admin.js
document.addEventListener("DOMContentLoaded", () => {
  // ── Leaflet map ──────────────────────────────────────────
  const map = L.map("map").setView([45.75, 21.23], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
              { attribution: "&copy; OpenStreetMap contributors" })
    .addTo(map);

  const markers = new Map();   // id → Leaflet marker

  // ── Modal elements ───────────────────────────────────────
  const modal      = document.getElementById("placeModal");
  const form       = document.getElementById("placeForm");
  const idField    = document.getElementById("placeId");
  const nameField  = document.getElementById("name");
  const typeField  = document.getElementById("type");
  const capField   = document.getElementById("capacity");
  const deleteBtn  = document.getElementById("deleteBtn");
  const cancelBtn  = document.getElementById("cancelBtn");

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
      capField.value     = place.capacity;
      currentLat         = place.lat;
      currentLon         = place.lon;
      deleteBtn.classList.remove("hidden");
    } else {                     // creating
      idField.value = "";
      nameField.value = typeField.value = capField.value = "";
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
      capacity: Number(capField.value) || 0,
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
