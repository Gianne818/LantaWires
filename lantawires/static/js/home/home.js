// LantaWires Home Dashboard Interactive Engine

document.addEventListener("DOMContentLoaded", () => {
  // Parse initial data injected from Django
  const reportsDataEl = document.getElementById("reports-data");
  const presetsDataEl = document.getElementById("presets-data");
  const categoriesDataEl = document.getElementById("categories-data");

  let reports = reportsDataEl ? JSON.parse(reportsDataEl.textContent) : [];
  const presets = presetsDataEl ? JSON.parse(presetsDataEl.textContent) : [];
  const categories = categoriesDataEl ? JSON.parse(categoriesDataEl.textContent) : [];
  
  let currentSelectedReport = reports.length > 0 ? reports[0] : null;
  let activeTab = "map"; // 'map' or 'feed'

  // DOM references
  const mapPinsContainer = document.getElementById("map-pins-container");
  let leafletMap = null;
  let leafletMarkersGroup = null;

  const BARANGAY_CENTROIDS = {
    "Tisa": [10.2982, 123.8741],
    "Buhisan": [10.2891, 123.8633],
    "Lahug": [10.3298, 123.9056],
    "Guadalupe": [10.3223, 123.8812],
    "Mabolo": [10.3189, 123.9145],
    "Kasambagan": [10.3242, 123.9118],
    "Banilad": [10.3394, 123.9115],
    "Punta Princesa": [10.2931, 123.8715],
    "Labangon": [10.3015, 123.8802],
    "Sambag I": [10.3105, 123.8901],
    "Sambag II": [10.3135, 123.8925],
    "Talamban": [10.3644, 123.9172],
    "Tejero": [10.3038, 123.9082],
    "Pari-an": [10.2995, 123.9038],
    "Carreta": [10.3081, 123.9103],
    "San Nicolas Proper": [10.2965, 123.8942],
    "Mambaling": [10.2912, 123.8804],
    "Basak San Nicolas": [10.2882, 123.8752],
    "Basak Pardo": [10.2825, 123.8682],
    "Cogon Ramos": [10.3115, 123.8975],
    "Capitol Site": [10.3175, 123.8912],
    "Kamputhaw": [10.3205, 123.8982],
    "Apas": [10.3341, 123.9085],
  };

  // Cebu City administrative & metropolitan bounds
  const CEBU_CITY_BOUNDS = typeof L !== "undefined" ? L.latLngBounds(
    [10.2200, 123.7500], // Southwest: Pardo / Inayawan / mountain limits
    [10.4500, 124.0100]  // Northeast: Talamban / Pit-os / coastal limits
  ) : null;

  function initLeafletMap() {
    const mapEl = document.getElementById("leaflet-map");
    if (!mapEl || typeof L === "undefined") return;

    try {
      const cebuBounds = L.latLngBounds(
        [10.2200, 123.7500],
        [10.4500, 124.0100]
      );

      leafletMap = L.map("leaflet-map", {
        center: [10.3157, 123.8854], // Cebu City Center
        zoom: 13,
        minZoom: 12, // Locked: cannot zoom out away from Cebu City
        maxZoom: 20, // Deep street/pole-level zoom enabled
        maxBounds: cebuBounds,
        maxBoundsViscosity: 0.9, // Firm bounce: cannot pan outside Cebu City
        zoomControl: false,
      });

      L.control.zoom({ position: "topright" }).addTo(leafletMap);

      // Official OpenStreetMap (Humanitarian OSM Cartography - 100% genuine OpenStreetMap, no localhost block)
      L.tileLayer("https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png", {
        maxNativeZoom: 19,
        maxZoom: 20, // Scales up smoothly for deep street inspection
        subdomains: ["a", "b", "c"],
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(leafletMap);

      leafletMarkersGroup = L.layerGroup().addTo(leafletMap);

      const coordsBadge = document.getElementById("map-coords-badge");
      leafletMap.on("move", () => {
        if (coordsBadge) {
          const center = leafletMap.getCenter();
          coordsBadge.textContent = `${center.lat.toFixed(4)}° N, ${center.lng.toFixed(4)}° E`;
        }
      });
    } catch (e) {
      console.warn("Leaflet initialization warning:", e);
    }
  }
  const incidentCardsContainer = document.getElementById("incident-cards-container");
  const searchInput = document.getElementById("search-incidents-input");
  const barangaySelect = document.getElementById("filter-barangay-select");
  const severitySelect = document.getElementById("filter-severity-select");
  const statusSelect = document.getElementById("filter-status-select");
  const viewMapBtn = document.getElementById("view-map-btn");
  const viewListBtn = document.getElementById("view-list-btn");
  const mapViewSection = document.getElementById("map-view-section");
  const feedViewSection = document.getElementById("feed-view-section");
  const feedCountEl = document.getElementById("feed-count");
  const cardsCountPill = document.getElementById("cards-count-pill");

  // Preview elements & role
  const dashboardRoot = document.getElementById("home-dashboard-root");
  const previewCard = document.getElementById("selected-hotspot-preview");
  const isResolver = (previewCard?.dataset.role || dashboardRoot?.dataset.role) === "resolver";
  const currentUserId = dashboardRoot?.dataset.userId || "";
  const currentUserEmail = (dashboardRoot?.dataset.userEmail || "").trim().toLowerCase();
  const previewImage = document.getElementById("preview-image");
  const previewTicket = document.getElementById("preview-ticket");
  const previewSeverityBadge = document.getElementById("preview-severity-badge");
  const previewBarangay = document.getElementById("preview-barangay");
  const previewTitle = document.getElementById("preview-title");
  const previewAddress = document.getElementById("preview-address");
  const previewInspectBtn = document.getElementById("preview-inspect-btn");

  // Report Modal elements
  const reportModal = document.getElementById("report-hazard-modal");
  const reportHeroBtn = document.getElementById("report-hazard-hero-btn");
  const closeReportModalBtn = document.getElementById("close-report-modal-btn");
  const cancelReportBtn = document.getElementById("cancel-report-btn");
  const startAiBtn = document.getElementById("start-ai-analysis-btn");
  const confirmDispatchBtn = document.getElementById("confirm-dispatch-btn");
  const stepInput = document.getElementById("report-step-input");
  const stepLoading = document.getElementById("report-step-loading");
  const stepResult = document.getElementById("report-step-result");
  const wizardPhotoPreview = document.getElementById("wizard-photo-preview");
  const wizardPhotoBadge = document.getElementById("wizard-photo-badge");
  const wizardCustomFile = document.getElementById("wizard-custom-file");
  const wizardTitleInput = document.getElementById("wizard-title-input");
  const wizardBarangaySelect = document.getElementById("wizard-barangay-select");
  const wizardAddressInput = document.getElementById("wizard-address-input");
  const wizardHazardTypeSelect = document.getElementById("wizard-hazard-type-select");
  const wizardSeveritySelect = document.getElementById("wizard-severity-select");
  const wizardClearanceInput = document.getElementById("wizard-clearance-input");
  const wizardGpsDisplay = document.getElementById("wizard-gps-display");
  const wizardGeolocateBtn = document.getElementById("wizard-geolocate-btn");
  const wizardMapCenterBtn = document.getElementById("wizard-map-center-btn");
  const wizardPresetButtons = document.querySelectorAll(".wizard-preset-btn");
  const aiLoadingSubtext = document.getElementById("ai-loading-subtext");
  const aiProgressBar = document.getElementById("ai-progress-bar");
  const resConfidence = document.getElementById("res-confidence");
  const resSag = document.getElementById("res-sag");
  const resCategory = document.getElementById("res-category");
  const resSeverity = document.getElementById("res-severity");

  // Detail Modal elements
  const detailModal = document.getElementById("incident-detail-modal");
  const closeDetailModalBtn = document.getElementById("close-detail-modal-btn");
  const closeDetailFooterBtn = document.getElementById("close-detail-footer-btn");
  const detailTicket = document.getElementById("detail-ticket");
  const detailSeverityBadge = document.getElementById("detail-severity-badge");
  const detailStatusBadge = document.getElementById("detail-status-badge");
  const detailTitle = document.getElementById("detail-title");
  const detailImage = document.getElementById("detail-image");
  const detailSag = document.getElementById("detail-sag");
  const detailDensity = document.getElementById("detail-density");
  const detailConfidence = document.getElementById("detail-confidence");
  const detailWarning = document.getElementById("detail-warning");
  const detailAction = document.getElementById("detail-action");
  const detailTurnaround = document.getElementById("detail-turnaround");
  const detailRecipientsList = document.getElementById("detail-recipients-list");
  const toggleStatusBtn = document.getElementById("toggle-incident-status-btn");
  const detailManageControls = document.getElementById("detail-manage-controls");
  const editIncidentBtn = document.getElementById("edit-incident-btn");
  const deleteIncidentBtn = document.getElementById("delete-incident-btn");
  const deleteConfirmBar = document.getElementById("delete-confirm-bar");
  const confirmDeleteIncidentBtn = document.getElementById("confirm-delete-incident-btn");
  const cancelDeleteIncidentBtn = document.getElementById("cancel-delete-incident-btn");
  const detailEditForm = document.getElementById("detail-edit-form");
  const detailEditTitle = document.getElementById("detail-edit-title");
  const detailEditBarangay = document.getElementById("detail-edit-barangay");
  const detailEditAddress = document.getElementById("detail-edit-address");
  const detailEditHazardType = document.getElementById("detail-edit-hazard-type");
  const detailEditSeverity = document.getElementById("detail-edit-severity");
  const detailEditClearance = document.getElementById("detail-edit-clearance");
  const detailEditError = document.getElementById("detail-edit-error");
  const detailEditCancelBtn = document.getElementById("detail-edit-cancel-btn");
  const detailEditSaveBtn = document.getElementById("detail-edit-save-btn");

  // Helper: Get CSRF token
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  // Helper: Escape HTML for safe template interpolation
  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Helper: Map Coordinates projection
  function getMapCoordinates(lat, lng) {
    const minLat = 10.280, maxLat = 10.345, minLng = 123.850, maxLng = 123.925;
    const xPercent = ((lng - minLng) / (maxLng - minLng)) * 100;
    const yPercent = (1 - (lat - minLat) / (maxLat - minLat)) * 100;
    return {
      x: Math.max(10, Math.min(90, xPercent)),
      y: Math.max(12, Math.min(88, yPercent)),
    };
  }

  // Helper: Severity Badge config
  function getSeverityConfig(sev) {
    switch (sev) {
      case "critical":
        return { label: "CRITICAL", bg: "#ff6b6b", badgeClass: "badge-critical" };
      case "high":
        return { label: "HIGH", bg: "#ff8f5e", badgeClass: "badge-high" };
      case "medium":
        return { label: "MEDIUM", bg: "#8a94a8", badgeClass: "badge-medium" };
      default:
        return { label: "RESOLVED", bg: "#2fb37c", badgeClass: "badge-resolved" };
    }
  }

  // Helper: Status label config — short labels to avoid wrapping
  function getStatusConfig(status) {
    switch (status) {
      case "ai_verified":
        return { label: "Verified", badgeClass: "badge-amber" };
      case "dispatched":
        return { label: "Dispatched", badgeClass: "badge-amber" };
      case "under_inspection":
      case "investigating":
        return { label: "Investigating", badgeClass: "badge-high" };
      case "resolved":
        return { label: "Resolved", badgeClass: "badge-resolved" };
      default:
        return { label: status, badgeClass: "badge-amber" };
    }
  }

  // Filtering function
  function getFilteredReports() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    const selectedBarangay = barangaySelect ? barangaySelect.value : "all";
    const selectedSeverity = severitySelect ? severitySelect.value : "all";
    const selectedStatus = statusSelect ? statusSelect.value : "all";

    return reports.filter(r => {
      if (selectedBarangay !== "all" && r.barangay !== selectedBarangay) return false;
      if (selectedSeverity !== "all" && r.severity !== selectedSeverity) return false;
      if (selectedStatus !== "all" && r.status !== selectedStatus) return false;
      if (query) {
        const titleMatch = (r.title || "").toLowerCase().includes(query);
        const ticketMatch = (r.ticketNumber || "").toLowerCase().includes(query);
        const addressMatch = (r.address || "").toLowerCase().includes(query);
        const brgyMatch = (r.barangay || "").toLowerCase().includes(query);
        return titleMatch || ticketMatch || addressMatch || brgyMatch;
      }
      return true;
    });
  }

  // Render Map Pins
  function renderMapPins() {
    const filtered = getFilteredReports();

    if (leafletMap && leafletMarkersGroup) {
      leafletMarkersGroup.clearLayers();

      filtered.forEach(report => {
        const lat = report.gpsCoordinates?.lat || 10.2982;
        const lng = report.gpsCoordinates?.lng || 123.8741;
        const isCritical = report.severity === "critical";
        const isSelected = currentSelectedReport && currentSelectedReport.id === report.id;
        const sevConfig = getSeverityConfig(report.severity);

        const customIcon = L.divIcon({
          className: "custom-leaflet-marker",
          html: `
            <div class="custom-leaflet-pin">
              <div class="map-pin ${isSelected ? "active" : ""}">
                ${isCritical ? '<span class="map-pin-pulse"></span>' : ""}
                <div class="map-pin-head" style="background: ${sevConfig.bg};">
                  <i data-lucide="${report.status === "resolved" ? "check" : "alert-triangle"}" style="width: 14px; height: 14px; stroke-width: 2.5;"></i>
                </div>
              </div>
            </div>
          `,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
          popupAnchor: [0, -18],
        });

        const marker = L.marker([lat, lng], { icon: customIcon });

        const popupHtml = `
          <div style="font-family: inherit; font-size: 0.8rem; min-width: 170px; line-height: 1.35; padding: 2px;">
            <div style="font-weight: 800; font-size: 0.84rem; margin-bottom: 2px; color: var(--ink);">${escapeHtml(report.title)}</div>
            <div style="color: var(--ink-2); font-size: 0.72rem; margin-bottom: 6px;">Brgy. ${escapeHtml(report.barangay)}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
              <span class="badge-pill ${sevConfig.badgeClass}" style="font-size: 0.65rem; padding: 2px 7px;">${sevConfig.label}</span>
              <span style="font-weight: 700; color: var(--red); font-size: 0.74rem; font-variant-numeric: tabular-nums;">${report.clearanceHeightMeters || 3.1}m clearance</span>
            </div>
          </div>
        `;
        marker.bindPopup(popupHtml);

        marker.on("click", () => {
          selectReport(report, false, true);
        });

        marker.addTo(leafletMarkersGroup);
      });

      if (window.lucide) window.lucide.createIcons();
      return;
    }

    if (!mapPinsContainer) return;
    mapPinsContainer.innerHTML = "";

    filtered.forEach(report => {
      const coords = getMapCoordinates(
        report.gpsCoordinates?.lat || 10.2982,
        report.gpsCoordinates?.lng || 123.8741
      );
      const isCritical = report.severity === "critical";
      const isSelected = currentSelectedReport && currentSelectedReport.id === report.id;
      const sevConfig = getSeverityConfig(report.severity);

      const pinEl = document.createElement("div");
      pinEl.className = `map-pin ${isSelected ? "active" : ""}`;
      pinEl.style.left = `${coords.x}%`;
      pinEl.style.top = `${coords.y}%`;

      pinEl.innerHTML = `
        ${isCritical ? '<span class="map-pin-pulse"></span>' : ''}
        <div class="map-pin-head" style="background: ${sevConfig.bg};">
          <i data-lucide="${report.status === 'resolved' ? 'check' : 'alert-triangle'}" style="width: 14px; height: 14px; stroke-width: 2.5;"></i>
        </div>
      `;

      pinEl.addEventListener("click", () => {
        selectReport(report, true, true);
      });

      mapPinsContainer.appendChild(pinEl);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  // Render Incident Cards Grid — paginated, no ticket IDs on cards
  let visibleCount = 6;
  const PAGE_SIZE = 6;
  function renderIncidentCards(reset) {
    if (!incidentCardsContainer) return;
    if (reset) visibleCount = PAGE_SIZE;
    incidentCardsContainer.innerHTML = "";

    const filtered = getFilteredReports();
    if (feedCountEl) feedCountEl.textContent = filtered.length;
    if (cardsCountPill) cardsCountPill.textContent = `${filtered.length} incidents`;

    if (filtered.length === 0) {
      incidentCardsContainer.innerHTML = `
        <div class="clay-card" style="grid-column: 1 / -1; padding: 2.2rem 1.5rem; text-align: center; border-radius: 20px;">
          <img src="/static/images/mascot-sparrow.svg" alt="All clear" style="width: 110px; margin: 0 auto .6rem;" />
          <p style="font-size: 0.95rem; font-weight: 800;">All clear in Cebu! Wiry found nothing.</p>
          <p class="section-sub" style="margin-top: 0.3rem;">Try a different search or barangay.</p>
        </div>
      `;
      return;
    }

    filtered.slice(0, visibleCount).forEach(report => {
      const sevConfig = getSeverityConfig(report.severity);
      const statusConfig = getStatusConfig(report.status);
      const clearanceText = (report.aiAnalysis?.cableSagClearance || "3.2m above road").split("(")[0].trim();
      const confidenceValue = report.aiAnalysis?.confidence || 95.4;

      const card = document.createElement("div");
      card.className = "clay-card incident-card";
      card.setAttribute("tabindex", "0");
      card.setAttribute("role", "button");
      card.setAttribute("aria-label", `${report.title} in Brgy. ${report.barangay}`);

      const fallbackImg = "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80";
      const thumbImg = report.imageUrl || fallbackImg;

      card.innerHTML = `
        <div>
          <div class="incident-card-thumb">
            <img src="${escapeHtml(thumbImg)}" alt="${escapeHtml(report.title)}" loading="lazy" onerror="this.src='${fallbackImg}'" />
            <div class="incident-card-thumb-badges">
              <span class="badge-pill badge-compact ${sevConfig.badgeClass}">${sevConfig.label}</span>
              <span class="badge-pill badge-compact ${statusConfig.badgeClass}">${statusConfig.label}</span>
            </div>
          </div>

          <h3 class="incident-card-title">${escapeHtml(report.title)}</h3>

          <p class="incident-card-address">
            <i data-lucide="map-pin" style="width: 13px; height: 13px; flex-shrink: 0;"></i>
            <span>${escapeHtml(report.address)}</span>
          </p>

          <div class="clay-inset-box incident-telemetry">
            <div class="incident-telemetry-row">
              <span class="incident-telemetry-label">Clearance</span>
              <span class="incident-telemetry-value is-clearance">${escapeHtml(clearanceText)}</span>
            </div>
            <div class="incident-telemetry-row">
              <span class="incident-telemetry-label">Confidence</span>
              <span class="incident-telemetry-value is-confidence">${escapeHtml(confidenceValue)}%</span>
            </div>
          </div>
        </div>

        <div class="incident-card-footer">
          <span>${escapeHtml(report.reportedAt)}</span>
          <span class="incident-card-action">
            <span>${isResolver ? "Inspect" : "Safety details"}</span>
            <i data-lucide="chevron-right" style="width: 13px; height: 13px;"></i>
          </span>
        </div>
      `;

      card.addEventListener("click", () => {
        openDetailModal(report);
      });
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openDetailModal(report);
        }
      });

      incidentCardsContainer.appendChild(card);
    });

    // Show-more pagination
    const remaining = filtered.length - visibleCount;
    let moreBtn = document.getElementById("show-more-hazards-btn");
    if (remaining > 0) {
      if (!moreBtn) {
        moreBtn = document.createElement("button");
        moreBtn.id = "show-more-hazards-btn";
        moreBtn.type = "button";
        moreBtn.className = "clay-btn-ghost";
        moreBtn.style.cssText = "grid-column: 1 / -1; justify-self: center; margin-top: .25rem;";
        moreBtn.addEventListener("click", () => { visibleCount += PAGE_SIZE; renderIncidentCards(false); });
        incidentCardsContainer.appendChild(moreBtn);
      }
      moreBtn.innerHTML = `<span>Show more (${remaining} remaining)</span>`;
      moreBtn.style.display = "inline-flex";
    } else if (moreBtn) {
      moreBtn.style.display = "none";
    }

    if (window.lucide) window.lucide.createIcons();
  }

  // Select Report on Map
  function selectReport(report, panMap = true, showPreview = true) {
    currentSelectedReport = report;

    if (panMap && leafletMap && report && report.gpsCoordinates) {
      leafletMap.panTo([report.gpsCoordinates.lat, report.gpsCoordinates.lng], { animate: true, duration: 0.6 });
    }

    if (previewCard && report) {
      previewCard.style.display = showPreview ? "flex" : "none";
      if (previewImage) {
        previewImage.onerror = function() {
          this.src = "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80";
        };
        previewImage.src = report.imageUrl || "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80";
      }
      if (previewTicket) {
        if (isResolver) {
          previewTicket.style.display = "inline-flex";
          previewTicket.textContent = report.ticketNumber;
        } else {
          previewTicket.style.display = "none";
          previewTicket.textContent = "";
        }
      }
      if (previewBarangay) previewBarangay.textContent = `Brgy. ${report.barangay}`;
      if (previewTitle) previewTitle.textContent = report.title;
      if (previewAddress) previewAddress.textContent = report.address;

      const sevConfig = getSeverityConfig(report.severity);
      if (previewSeverityBadge) {
        previewSeverityBadge.className = `badge-pill badge-compact ${sevConfig.badgeClass}`;
        previewSeverityBadge.textContent = sevConfig.label;
      }
      if (previewInspectBtn) {
        const inspectLabel = previewInspectBtn.querySelector("span");
        if (inspectLabel) inspectLabel.textContent = isResolver ? "Inspect" : "Safety details";
      }
    }
  }

  if (previewInspectBtn) {
    previewInspectBtn.addEventListener("click", () => {
      if (currentSelectedReport) {
        openDetailModal(currentSelectedReport);
      }
    });
  }

  // Open Incident Detail Modal
  function openDetailModal(report) {
    if (!report || !detailModal) return;
    currentSelectedReport = report;

    const sevConfig = getSeverityConfig(report.severity);
    const statusConfig = getStatusConfig(report.status);

    if (detailTicket) detailTicket.textContent = report.ticketNumber;
    if (detailTitle) detailTitle.textContent = report.title;
    if (detailImage) {
      detailImage.onerror = function() {
        this.src = "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80";
      };
      detailImage.src = report.imageUrl || "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80";
    }

    if (detailSeverityBadge) {
      detailSeverityBadge.className = `badge-pill ${sevConfig.badgeClass}`;
      detailSeverityBadge.textContent = sevConfig.label;
    }
    if (detailStatusBadge) {
      detailStatusBadge.className = `badge-pill ${statusConfig.badgeClass}`;
      detailStatusBadge.textContent = statusConfig.label;
    }

    if (detailSag) detailSag.textContent = report.aiAnalysis?.cableSagClearance || "3.1m above asphalt";
    if (detailDensity) detailDensity.textContent = report.aiAnalysis?.wireDensityScore || "High (35+ cables)";
    if (detailConfidence) detailConfidence.textContent = `${report.aiAnalysis?.confidence || 96.2}%`;
    if (detailWarning) detailWarning.textContent = report.aiAnalysis?.safetyWarning || "Direct road obstruction risk.";
    if (detailAction) detailAction.textContent = report.aiAnalysis?.recommendedAction || "Utility truck re-tensioning.";
    if (detailTurnaround) detailTurnaround.textContent = `Turnaround: ${report.dispatchDetails?.dispatchTurnaroundSeconds || 36}s`;

    // Render recipients
    if (detailRecipientsList) {
      detailRecipientsList.innerHTML = "";
      const recipients = report.dispatchDetails?.recipients || [
        { agency: "Cebu City TIC Desk", department: "Wire Eradication", email: "dispatch@cebucity.gov.ph", status: "Delivered" },
        { agency: "Visayan Electric (VECO)", department: "Maintenance Squad", email: "emergency@veco.com.ph", status: "Delivered" }
      ];

      recipients.forEach(r => {
        const item = document.createElement("div");
        item.style.cssText = "display: flex; justify-content: space-between; align-items: center;";
        item.innerHTML = `
          <span><strong>${escapeHtml(r.agency)}</strong></span>
          <span style="color: var(--green); font-weight: 800;">✓ ${escapeHtml(r.status || "Delivered")}</span>
        `;
        detailRecipientsList.appendChild(item);
      });
    }

    if (detailEditForm) detailEditForm.style.display = "none";
    if (detailEditError) detailEditError.style.display = "none";
    if (deleteConfirmBar) deleteConfirmBar.style.display = "none";
    if (detailManageControls) {
      const allowed = canManageReport(report);
      detailManageControls.style.display = allowed ? "flex" : "none";
      if (deleteIncidentBtn) {
        const delLabel = deleteIncidentBtn.querySelector("span");
        if (delLabel) delLabel.textContent = isResolver ? "Delete" : "Withdraw";
      }
    }

    pendingSelectedStatus = report.status;
    syncStageSelectionUI(pendingSelectedStatus, report.status);

    detailModal.classList.add("open");
    document.documentElement.classList.add("modal-open");
    document.body.classList.add("modal-open");
    if (window.lucide) window.lucide.createIcons();
  }

  function canManageReport(report) {
    if (!report || !report.dbId) return false;
    if (isResolver) return true;
    const ownsById = Boolean(currentUserId && report.reporterId != null && String(report.reporterId) === String(currentUserId));
    const ownsByEmail = Boolean(currentUserEmail && (report.reporterEmail || "").toLowerCase() === currentUserEmail);
    if (!ownsById && !ownsByEmail) return false;
    return report.status !== "resolved";
  }

  let pendingSelectedStatus = null;
  const saveStatusBtn = document.getElementById("save-incident-status-btn");

  function syncStageSelectionUI(selectedStatus, savedStatus) {
    const stageButtons = document.querySelectorAll(".status-stage-btn");
    stageButtons.forEach(btn => {
      const btnStatus = btn.getAttribute("data-status");
      if (btnStatus === selectedStatus) {
        btn.style.borderColor = "var(--peach)";
        btn.style.background = "var(--peach-bg)";
      } else {
        btn.style.borderColor = "";
        btn.style.background = "";
      }
    });
    if (saveStatusBtn) {
      const hasChange = Boolean(selectedStatus && selectedStatus !== savedStatus);
      saveStatusBtn.disabled = !hasChange;
      saveStatusBtn.style.opacity = hasChange ? "1" : "0.5";
      saveStatusBtn.innerHTML = `<i data-lucide="save" style="width: 14px; height: 14px;"></i><span>${hasChange ? "Save status" : "Save status"}</span>`;
      if (window.lucide) window.lucide.createIcons();
    }
  }

  function syncBodyModalLock() {
    const anyOpen = (detailModal && detailModal.classList.contains("open")) || (reportModal && reportModal.classList.contains("open"));
    document.documentElement.classList.toggle("modal-open", Boolean(anyOpen));
    document.body.classList.toggle("modal-open", Boolean(anyOpen));
  }

  function closeDetailModal() {
    pendingSelectedStatus = null;
    if (detailEditForm) detailEditForm.style.display = "none";
    if (deleteConfirmBar) deleteConfirmBar.style.display = "none";
    if (detailModal) detailModal.classList.remove("open");
    syncBodyModalLock();
  }

  if (editIncidentBtn && detailEditForm) {
    editIncidentBtn.addEventListener("click", () => {
      if (!currentSelectedReport || !canManageReport(currentSelectedReport)) return;
      if (deleteConfirmBar) deleteConfirmBar.style.display = "none";
      if (detailEditError) detailEditError.style.display = "none";
      if (detailEditTitle) detailEditTitle.value = currentSelectedReport.title || "";
      if (detailEditBarangay) detailEditBarangay.value = currentSelectedReport.barangay || "Tisa";
      if (detailEditAddress) detailEditAddress.value = currentSelectedReport.address || "";
      if (detailEditHazardType) detailEditHazardType.value = currentSelectedReport.hazardType || "sagging_cable";
      if (detailEditSeverity) detailEditSeverity.value = currentSelectedReport.severity || "critical";
      if (detailEditClearance) detailEditClearance.value = currentSelectedReport.clearanceHeightMeters ?? 3.0;
      detailEditForm.style.display = "flex";
      if (detailEditTitle) detailEditTitle.focus();
    });
  }

  if (detailEditCancelBtn && detailEditForm) {
    detailEditCancelBtn.addEventListener("click", () => {
      detailEditForm.style.display = "none";
      if (detailEditError) detailEditError.style.display = "none";
    });
  }

  if (detailEditForm) {
    detailEditForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!currentSelectedReport || !currentSelectedReport.dbId) return;
      if (detailEditError) detailEditError.style.display = "none";
      if (detailEditSaveBtn) detailEditSaveBtn.disabled = true;

      try {
        const res = await fetch(`/home/api/report/${currentSelectedReport.dbId}/edit/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({
            title: detailEditTitle ? detailEditTitle.value.trim() : "",
            barangay: detailEditBarangay ? detailEditBarangay.value : "",
            address: detailEditAddress ? detailEditAddress.value.trim() : "",
            hazardType: detailEditHazardType ? detailEditHazardType.value : "sagging_cable",
            severity: detailEditSeverity ? detailEditSeverity.value : "critical",
            clearanceHeightMeters: detailEditClearance ? Number(detailEditClearance.value) : 3.0,
          }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          if (detailEditError) {
            detailEditError.textContent = data.message || "Unable to update report.";
            detailEditError.style.display = "block";
          }
          return;
        }
        const updatedRep = data.report;
        reports = reports.map(r => (r.dbId === updatedRep.dbId || r.id === updatedRep.id) ? updatedRep : r);
        currentSelectedReport = updatedRep;
        openDetailModal(updatedRep);
        renderMapPins();
        renderIncidentCards(false);
        updateStats();
        selectReport(updatedRep, false, previewCard && previewCard.style.display !== "none");
      } catch (err) {
        if (detailEditError) {
          detailEditError.textContent = "Network error while saving report changes.";
          detailEditError.style.display = "block";
        }
      } finally {
        if (detailEditSaveBtn) detailEditSaveBtn.disabled = false;
      }
    });
  }

  if (deleteIncidentBtn && deleteConfirmBar) {
    deleteIncidentBtn.addEventListener("click", () => {
      if (!currentSelectedReport || !canManageReport(currentSelectedReport)) return;
      if (detailEditForm) detailEditForm.style.display = "none";
      deleteConfirmBar.style.display = deleteConfirmBar.style.display === "flex" ? "none" : "flex";
    });
  }

  if (cancelDeleteIncidentBtn && deleteConfirmBar) {
    cancelDeleteIncidentBtn.addEventListener("click", () => {
      deleteConfirmBar.style.display = "none";
    });
  }

  if (confirmDeleteIncidentBtn) {
    confirmDeleteIncidentBtn.addEventListener("click", async () => {
      if (!currentSelectedReport || !currentSelectedReport.dbId) return;
      confirmDeleteIncidentBtn.disabled = true;
      try {
        const res = await fetch(`/home/api/report/${currentSelectedReport.dbId}/delete/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
        });
        if (res.ok) {
          const deletedDbId = currentSelectedReport.dbId;
          reports = reports.filter(r => r.dbId !== deletedDbId);
          currentSelectedReport = reports.length > 0 ? reports[0] : null;
          closeDetailModal();
          renderMapPins();
          renderIncidentCards(true);
          updateStats();
          if (currentSelectedReport) {
            selectReport(currentSelectedReport, false, isResolver);
          } else if (previewCard) {
            previewCard.style.display = "none";
          }
        } else {
          const data = await res.json().catch(() => ({}));
          alert(data.message || "Unable to delete report.");
        }
      } finally {
        confirmDeleteIncidentBtn.disabled = false;
      }
    });
  }

  if (closeDetailModalBtn) closeDetailModalBtn.addEventListener("click", closeDetailModal);
  if (closeDetailFooterBtn) closeDetailFooterBtn.addEventListener("click", closeDetailModal);
  if (detailModal) {
    detailModal.addEventListener("click", (e) => {
      if (e.target === detailModal) closeDetailModal();
    });
  }

  // 3-Stage Resolver Status Controls (select first, then Save status persists to DB)
  const statusStageButtons = document.querySelectorAll(".status-stage-btn");
  async function updateReportStatus(nextStatus) {
    if (!currentSelectedReport || !nextStatus) return;
    if (saveStatusBtn) {
      saveStatusBtn.disabled = true;
      saveStatusBtn.innerHTML = `<span>Saving...</span>`;
    }
    try {
      const res = await fetch("/home/api/status/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          reportId: currentSelectedReport.id,
          newStatus: nextStatus,
        }),
      });
      if (res.ok) {
        currentSelectedReport.status = nextStatus;
        reports = reports.map(r => r.id === currentSelectedReport.id ? { ...r, status: nextStatus } : r);
        openDetailModal(currentSelectedReport);
        renderMapPins();
        renderIncidentCards(false);
        updateStats();
        if (saveStatusBtn) {
          saveStatusBtn.innerHTML = `<i data-lucide="check" style="width: 14px; height: 14px;"></i><span>Saved</span>`;
          if (window.lucide) window.lucide.createIcons();
        }
      }
    } catch (err) {
      console.error("Status update error:", err);
      syncStageSelectionUI(pendingSelectedStatus, currentSelectedReport.status);
    }
  }

  if (statusStageButtons.length > 0) {
    statusStageButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        if (!currentSelectedReport) return;
        pendingSelectedStatus = btn.getAttribute("data-status");
        syncStageSelectionUI(pendingSelectedStatus, currentSelectedReport.status);
      });
    });
  }
  if (saveStatusBtn) {
    saveStatusBtn.addEventListener("click", () => {
      if (!currentSelectedReport || !pendingSelectedStatus) return;
      if (pendingSelectedStatus === currentSelectedReport.status) return;
      updateReportStatus(pendingSelectedStatus);
    });
  }

  function updateStats() {
    const total = reports.length;
    const critical = reports.filter(r => r.severity === "critical").length;
    const dispatched = reports.filter(r => r.status === "dispatched").length;
    const investigating = reports.filter(r => r.status === "investigating").length;
    const resolved = reports.filter(r => r.status === "resolved").length;

    const elTotal = document.getElementById("stat-total");
    const elCrit = document.getElementById("stat-critical");
    const elDisp = document.getElementById("stat-dispatched");
    const elInv = document.getElementById("stat-investigating");
    const elRes = document.getElementById("stat-resolved");

    if (elTotal) elTotal.textContent = total;
    if (elCrit) elCrit.textContent = critical;
    if (elDisp) elDisp.textContent = dispatched;
    if (elInv) elInv.textContent = investigating;
    if (elRes) elRes.textContent = resolved;
  }

  // Report Wizard Logic
  let customUploadedImage = null;
  let wizardGps = null;
  let wizardAnalysisPayload = null;
  const photoUploadDropzone = document.getElementById("photo-upload-dropzone");
  const uploadPlaceholderContent = document.getElementById("upload-placeholder-content");
  const wizardPreviewOverlay = document.getElementById("wizard-preview-overlay");

  function setWizardGps(lat, lng, labelSuffix = "") {
    wizardGps = {
      lat: Number(Number(lat).toFixed(5)),
      lng: Number(Number(lng).toFixed(5)),
    };
    if (wizardGpsDisplay) {
      wizardGpsDisplay.textContent = `${wizardGps.lat.toFixed(4)}, ${wizardGps.lng.toFixed(4)}${labelSuffix}`;
    }
  }

  function syncWizardGpsFromBarangay() {
    const brgy = (wizardBarangaySelect ? wizardBarangaySelect.value : "") || "Tisa";
    const base = BARANGAY_CENTROIDS[brgy] || [10.2982, 123.8741];
    setWizardGps(base[0], base[1], ` · Brgy. ${brgy}`);
  }

  function getSelectedCategoryMeta() {
    const type = wizardHazardTypeSelect ? wizardHazardTypeSelect.value : "sagging_cable";
    return (
      categories.find(c => c.type === type) || {
        type,
        name: "Sagging Overhead Cable",
        min_clearance: 4.5,
        default_severity: "critical",
      }
    );
  }

  function computeWizardTelemetry() {
    const cat = getSelectedCategoryMeta();
    const rawClearance = wizardClearanceInput ? parseFloat(wizardClearanceInput.value) : 2.9;
    const clearance = Number.isFinite(rawClearance) ? Math.max(0.5, Math.min(15.0, rawClearance)) : 2.9;
    const severity = wizardSeveritySelect ? wizardSeveritySelect.value : cat.default_severity;
    const minCl = Number(cat.min_clearance || 4.5);
    const deficit = Math.max(0, minCl - clearance);
    const confidence = Number(Math.min(98.6, 92.4 + Math.min(5.2, deficit * 2.1)).toFixed(1));
    const isCritical = severity === "critical" || deficit >= 1.2;

    const componentsByType = {
      sagging_cable: ["Sagging drop cable", "Overhanging telecom loop", "Messenger wire slack"],
      low_clearance: ["Low vehicle-corridor sag", "Primary feeder encroachment", "PUJ clearance breach"],
      spaghetti_cluster: ["Overcrowded splice cluster", "Dead coax/fiber loops", "Pole overload"],
      broken_pole: ["Deflected utility pole", "Strained anchor guy wire", "Overburdened cable spool"],
      transformer_spark: ["Charred insulation jacket", "Secondary bus arcing zone", "Unauthorized tie-in"],
    };

    const actionByType = {
      sagging_cable: "Dispatch bucket truck for cable re-tensioning and messenger lashing.",
      low_clearance: "Priority street cordon and immediate elevation above 4.5m transit height.",
      spaghetti_cluster: "Joint TIC & telco dead-wire pruning and bundle consolidation.",
      broken_pole: "Emergency structural pole bracing and fiber load redistribution.",
      transformer_spark: "Immediate VECO de-energization, thermal isolation, and fire standby.",
    };

    const warning = isCritical
      ? `Clearance of ${clearance.toFixed(1)}m breaches the ${minCl.toFixed(1)}m legal minimum — direct vehicle/pedestrian hazard.`
      : `Clearance of ${clearance.toFixed(1)}m requires scheduled utility re-tensioning (standard: ${minCl.toFixed(1)}m).`;

    return {
      categoryName: cat.name,
      hazardType: cat.type,
      severity,
      clearance,
      confidence,
      sagClearance: `${clearance.toFixed(1)}m clearance (legal min: ${minCl.toFixed(1)}m)`,
      wireDensity: isCritical ? "Severe (Overlapping primary & telco bundles)" : "High (Multi-carrier bundle)",
      components: componentsByType[cat.type] || componentsByType.sagging_cable,
      safetyWarning: warning,
      recommendedAction: actionByType[cat.type] || actionByType.sagging_cable,
    };
  }

  function openReportModal() {
    if (!reportModal) return;
    customUploadedImage = null;
    wizardAnalysisPayload = null;
    wizardPresetButtons.forEach(b => b.classList.remove("selected-preset"));
    if (wizardCustomFile) wizardCustomFile.value = "";
    if (wizardPhotoPreview) {
      wizardPhotoPreview.src = "";
      wizardPhotoPreview.style.display = "none";
    }
    if (uploadPlaceholderContent) uploadPlaceholderContent.style.display = "block";
    if (wizardPreviewOverlay) wizardPreviewOverlay.style.display = "none";
    if (photoUploadDropzone) photoUploadDropzone.style.borderStyle = "dashed";
    if (wizardTitleInput) wizardTitleInput.value = "";
    if (wizardAddressInput) wizardAddressInput.value = "";
    if (wizardHazardTypeSelect) wizardHazardTypeSelect.value = "sagging_cable";
    if (wizardSeveritySelect) wizardSeveritySelect.value = "critical";
    if (wizardClearanceInput) wizardClearanceInput.value = "2.9";
    syncWizardGpsFromBarangay();
    setWizardStep("input");
    reportModal.classList.add("open");
    document.documentElement.classList.add("modal-open");
    document.body.classList.add("modal-open");
    if (window.lucide) lucide.createIcons();
  }

  if (wizardBarangaySelect) {
    wizardBarangaySelect.addEventListener("change", syncWizardGpsFromBarangay);
  }

  if (wizardHazardTypeSelect && wizardSeveritySelect) {
    wizardHazardTypeSelect.addEventListener("change", () => {
      const cat = getSelectedCategoryMeta();
      if (cat.default_severity) wizardSeveritySelect.value = cat.default_severity;
    });
  }

  if (wizardPresetButtons.length > 0) {
    wizardPresetButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        const idx = Number(btn.getAttribute("data-preset-index"));
        const preset = presets[idx];
        if (!preset) return;
        wizardPresetButtons.forEach(b => b.classList.remove("selected-preset"));
        btn.classList.add("selected-preset");

        if (wizardTitleInput) wizardTitleInput.value = preset.title || "";
        if (wizardBarangaySelect && preset.barangay) wizardBarangaySelect.value = preset.barangay;
        if (wizardAddressInput) wizardAddressInput.value = preset.address || "";
        if (wizardHazardTypeSelect && preset.hazardType) wizardHazardTypeSelect.value = preset.hazardType;
        if (wizardSeveritySelect && preset.severity) wizardSeveritySelect.value = preset.severity;
        if (wizardClearanceInput && preset.clearanceHeightMeters) wizardClearanceInput.value = preset.clearanceHeightMeters;
        syncWizardGpsFromBarangay();

        if (preset.imageUrl && wizardPhotoPreview) {
          customUploadedImage = preset.imageUrl;
          wizardPhotoPreview.src = preset.imageUrl;
          wizardPhotoPreview.style.display = "block";
          if (uploadPlaceholderContent) uploadPlaceholderContent.style.display = "none";
          if (wizardPreviewOverlay) wizardPreviewOverlay.style.display = "flex";
          if (wizardPhotoBadge) wizardPhotoBadge.textContent = `Sample · Brgy. ${preset.barangay}`;
          if (photoUploadDropzone) photoUploadDropzone.style.borderStyle = "solid";
        }
      });
    });
  }

  if (wizardGeolocateBtn) {
    wizardGeolocateBtn.addEventListener("click", () => {
      if (!navigator.geolocation) {
        if (wizardGpsDisplay) wizardGpsDisplay.textContent += " (GPS unavailable)";
        return;
      }
      if (wizardGpsDisplay) wizardGpsDisplay.textContent = "Locating device…";
      navigator.geolocation.getCurrentPosition(
        pos => {
          const { latitude, longitude } = pos.coords;
          if (CEBU_CITY_BOUNDS && CEBU_CITY_BOUNDS.contains([latitude, longitude])) {
            setWizardGps(latitude, longitude, " · Device GPS");
          } else {
            syncWizardGpsFromBarangay();
            if (wizardGpsDisplay) wizardGpsDisplay.textContent += " (Outside Cebu, using barangay)";
          }
        },
        () => {
          syncWizardGpsFromBarangay();
        },
        { enableHighAccuracy: true, timeout: 5000 }
      );
    });
  }

  if (wizardMapCenterBtn) {
    wizardMapCenterBtn.addEventListener("click", () => {
      if (leafletMap) {
        const center = leafletMap.getCenter();
        setWizardGps(center.lat, center.lng, " · Map pin");
      } else {
        syncWizardGpsFromBarangay();
      }
    });
  }

  function closeReportModal() {
    if (!reportModal) return;
    reportModal.classList.remove("open");
    syncBodyModalLock();
  }

  if (reportModal) {
    reportModal.addEventListener("click", (e) => {
      if (e.target === reportModal) closeReportModal();
    });
  }

  function setWizardStep(step) {
    if (stepInput) stepInput.style.display = step === "input" ? "flex" : "none";
    if (stepLoading) stepLoading.style.display = step === "loading" ? "block" : "none";
    if (stepResult) stepResult.style.display = step === "result" ? "flex" : "none";

    if (startAiBtn) startAiBtn.style.display = step === "input" ? "inline-flex" : "none";
    if (confirmDispatchBtn) confirmDispatchBtn.style.display = step === "result" ? "inline-flex" : "none";
  }

  if (reportHeroBtn) reportHeroBtn.addEventListener("click", openReportModal);
  if (closeReportModalBtn) closeReportModalBtn.addEventListener("click", closeReportModal);
  if (cancelReportBtn) cancelReportBtn.addEventListener("click", closeReportModal);

  // Photo Upload Dropzone Click & Drag
  if (photoUploadDropzone && wizardCustomFile) {
    photoUploadDropzone.addEventListener("click", (e) => {
      // Don't trigger if clicked directly on input
      if (e.target !== wizardCustomFile) {
        wizardCustomFile.click();
      }
    });

    photoUploadDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      photoUploadDropzone.style.borderColor = "var(--peach)";
      photoUploadDropzone.style.background = "var(--peach-soft)";
    });

    photoUploadDropzone.addEventListener("dragleave", (e) => {
      e.preventDefault();
      photoUploadDropzone.style.borderColor = "var(--clay-border)";
      photoUploadDropzone.style.background = "var(--clay-inset)";
    });

    photoUploadDropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      photoUploadDropzone.style.borderColor = "var(--clay-border)";
      photoUploadDropzone.style.background = "var(--clay-inset)";
      const files = e.dataTransfer?.files;
      if (files && files.length > 0) {
        handlePhotoFile(files[0]);
      }
    });
  }

  // Handle Photo File selection
  function handlePhotoFile(file) {
    if (!file || !file.type.startsWith("image/")) {
      alert("Please upload a valid image file (JPG, PNG, WEBP).");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      customUploadedImage = reader.result;
      if (wizardPhotoPreview) {
        wizardPhotoPreview.src = customUploadedImage;
        wizardPhotoPreview.style.display = "block";
      }
      if (uploadPlaceholderContent) uploadPlaceholderContent.style.display = "none";
      if (wizardPreviewOverlay) wizardPreviewOverlay.style.display = "flex";
      if (wizardPhotoBadge) {
        const brgy = wizardBarangaySelect ? wizardBarangaySelect.value : "Cebu";
        wizardPhotoBadge.textContent = `${file.name.slice(0, 16)}… · Brgy. ${brgy}`;
      }
      if (photoUploadDropzone) photoUploadDropzone.style.borderStyle = "solid";
      if (window.lucide) lucide.createIcons();
    };
    reader.readAsDataURL(file);
  }

  // Custom File Input change
  if (wizardCustomFile) {
    wizardCustomFile.addEventListener("change", e => {
      const file = e.target.files?.[0];
      if (file) handlePhotoFile(file);
    });
  }

  // Run AI Analysis Simulation
  if (startAiBtn) {
    startAiBtn.addEventListener("click", () => {
      setWizardStep("loading");

      let progress = 10;
      if (aiProgressBar) aiProgressBar.style.width = "10%";

      const subtexts = [
        "Scanning cable sag clearance and wire entanglement density...",
        "Identifying primary vs secondary drop lines...",
        "Calculating vertical clearance against PUJ corridor regulations...",
        "Generating multi-agency routing payload for TIC & VECO desks..."
      ];

      let stepIdx = 0;
      const interval = setInterval(() => {
        progress += 28;
        if (aiProgressBar) aiProgressBar.style.width = `${Math.min(progress, 100)}%`;
        stepIdx++;
        if (aiLoadingSubtext && subtexts[stepIdx]) {
          aiLoadingSubtext.textContent = subtexts[stepIdx];
        }

        if (progress >= 100) {
          clearInterval(interval);
          wizardAnalysisPayload = computeWizardTelemetry();
          setTimeout(() => {
            if (resConfidence) resConfidence.textContent = `${wizardAnalysisPayload.confidence}%`;
            if (resSag) resSag.textContent = wizardAnalysisPayload.sagClearance;
            if (resCategory) resCategory.textContent = wizardAnalysisPayload.categoryName;
            if (resSeverity) resSeverity.textContent = wizardAnalysisPayload.severity.toUpperCase();
            setWizardStep("result");
          }, 350);
        }
      }, 350);
    });
  }

  // Confirm Dispatch & Create Report API
  if (confirmDispatchBtn) {
    confirmDispatchBtn.addEventListener("click", async () => {
      confirmDispatchBtn.disabled = true;
      confirmDispatchBtn.innerHTML = `<span>Dispatching...</span>`;

      const telemetry = wizardAnalysisPayload || computeWizardTelemetry();
      const barangay = (wizardBarangaySelect ? wizardBarangaySelect.value : "") || "Tisa";
      const title = (wizardTitleInput ? wizardTitleInput.value.trim() : "") || `Low-hanging cable hazard - Brgy. ${barangay}`;
      const address = (wizardAddressInput ? wizardAddressInput.value.trim() : "") || `Brgy. ${barangay}, Cebu City`;
      const imageUrl = customUploadedImage || "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80";

      const baseCoords = BARANGAY_CENTROIDS[barangay] || [10.2982, 123.8741];
      const gps = wizardGps || {
        lat: Number(baseCoords[0].toFixed(5)),
        lng: Number(baseCoords[1].toFixed(5))
      };

      try {
        const response = await fetch("/home/api/report/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({
            title: title,
            barangay: barangay,
            address: address,
            gps: gps,
            severity: telemetry.severity,
            hazardType: telemetry.hazardType,
            clearanceHeightMeters: telemetry.clearance,
            imageUrl: imageUrl,
            confidence: telemetry.confidence,
            sagClearance: telemetry.sagClearance,
            wireDensity: telemetry.wireDensity,
            components: telemetry.components,
            safetyWarning: telemetry.safetyWarning,
            recommendedAction: telemetry.recommendedAction,
          }),
        });

        if (response.ok) {
          const resData = await response.json();
          const newRep = resData.report;

          reports.unshift(newRep);
          closeReportModal();

          // Refresh UI
          renderMapPins();
          renderIncidentCards(true);
          updateStats();
          selectReport(newRep, false, isResolver);
          if (leafletMap && newRep.gpsCoordinates) {
            leafletMap.flyTo([newRep.gpsCoordinates.lat, newRep.gpsCoordinates.lng], 16, { duration: 1.0 });
          }
          openDetailModal(newRep);
        } else {
          const errData = await response.json().catch(() => ({}));
          alert("Dispatch error: " + (errData.message || response.statusText || "Server error"));
        }
      } catch (err) {
        console.error("Dispatch error:", err);
        alert("Connection error while dispatching report.");
      } finally {
        confirmDispatchBtn.disabled = false;
        confirmDispatchBtn.innerHTML = `<span>Submit & dispatch</span>`;
        if (window.lucide) lucide.createIcons();
      }
    });
  }

  // Filter Listeners
  if (searchInput) searchInput.addEventListener("input", () => { renderMapPins(); renderIncidentCards(true); });
  if (barangaySelect) barangaySelect.addEventListener("change", () => {
    const b = barangaySelect.value;
    if (leafletMap && b in BARANGAY_CENTROIDS) {
      leafletMap.flyTo(BARANGAY_CENTROIDS[b], 15, { duration: 1.0 });
    } else if (leafletMap && b === "all") {
      leafletMap.flyTo([10.3157, 123.8854], 13, { duration: 1.0 });
    }
    renderMapPins();
    renderIncidentCards(true);
  });
  if (severitySelect) severitySelect.addEventListener("change", () => { renderMapPins(); renderIncidentCards(true); });
  if (statusSelect) statusSelect.addEventListener("change", () => { renderMapPins(); renderIncidentCards(true); });

  // View Switcher Tabs
  if (viewMapBtn && viewListBtn) {
    viewMapBtn.addEventListener("click", () => {
      activeTab = "map";
      viewMapBtn.classList.add("active");
      viewListBtn.classList.remove("active");

      if (mapViewSection) mapViewSection.style.display = "flex";
      if (feedViewSection) feedViewSection.style.display = "flex";
      setTimeout(() => { if (leafletMap) leafletMap.invalidateSize(); }, 80);
      renderMapPins();
    });

    viewListBtn.addEventListener("click", () => {
      activeTab = "feed";
      viewListBtn.classList.add("active");
      viewMapBtn.classList.remove("active");

      if (feedViewSection) {
        feedViewSection.scrollIntoView({ behavior: "smooth" });
      }
    });
  }

  // Escape key closes active modal
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (detailModal && detailModal.classList.contains("open")) closeDetailModal();
      if (reportModal && reportModal.classList.contains("open")) closeReportModal();
    }
  });

  // Initial render
  initLeafletMap();
  renderMapPins();
  renderIncidentCards();
  if (reports.length > 0) {
    selectReport(reports[0], false, isResolver);
  }
});
