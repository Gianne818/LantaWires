// LantaWires Home Dashboard Interactive Engine

document.addEventListener("DOMContentLoaded", () => {
  // Parse initial data injected from Django
  const reportsDataEl = document.getElementById("reports-data");
  const presetsDataEl = document.getElementById("presets-data");
  
  let reports = reportsDataEl ? JSON.parse(reportsDataEl.textContent) : [];
  const presets = presetsDataEl ? JSON.parse(presetsDataEl.textContent) : [];
  
  let currentSelectedReport = reports.length > 0 ? reports[0] : null;
  let activeTab = "map"; // 'map' or 'feed'

  // DOM references
  const mapPinsContainer = document.getElementById("map-pins-container");
  const incidentCardsContainer = document.getElementById("incident-cards-container");
  const searchInput = document.getElementById("search-incidents-input");
  const barangaySelect = document.getElementById("filter-barangay-select");
  const severitySelect = document.getElementById("filter-severity-select");
  const viewMapBtn = document.getElementById("view-map-btn");
  const viewListBtn = document.getElementById("view-list-btn");
  const mapViewSection = document.getElementById("map-view-section");
  const feedViewSection = document.getElementById("feed-view-section");
  const feedCountEl = document.getElementById("feed-count");
  const cardsCountPill = document.getElementById("cards-count-pill");

  // Preview elements
  const previewCard = document.getElementById("selected-hotspot-preview");
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
  const aiLoadingSubtext = document.getElementById("ai-loading-subtext");
  const aiProgressBar = document.getElementById("ai-progress-bar");
  const resConfidence = document.getElementById("res-confidence");
  const resSag = document.getElementById("res-sag");

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

  // Helper: Get CSRF token
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
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
        return { label: "CRITICAL", bg: "#f43f5e", badgeClass: "badge-critical" };
      case "high":
        return { label: "HIGH", bg: "#f59e0b", badgeClass: "badge-high" };
      case "medium":
        return { label: "MEDIUM", bg: "#eab308", badgeClass: "badge-medium" };
      default:
        return { label: "RESOLVED", bg: "#10b981", badgeClass: "badge-resolved" };
    }
  }

  // Helper: Status label config
  function getStatusConfig(status) {
    switch (status) {
      case "ai_verified":
        return { label: "AI Verified", badgeClass: "badge-amber" };
      case "dispatched":
        return { label: "Dispatched for Clearing", badgeClass: "badge-amber" };
      case "under_inspection":
        return { label: "Inspection Ongoing", badgeClass: "badge-high" };
      case "resolved":
        return { label: "Bundled & Elevated", badgeClass: "badge-resolved" };
      default:
        return { label: status, badgeClass: "badge-amber" };
    }
  }

  // Filtering function
  function getFilteredReports() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    const selectedBarangay = barangaySelect ? barangaySelect.value : "all";
    const selectedSeverity = severitySelect ? severitySelect.value : "all";

    return reports.filter(r => {
      if (selectedBarangay !== "all" && r.barangay !== selectedBarangay) return false;
      if (selectedSeverity !== "all" && r.severity !== selectedSeverity) return false;
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
    if (!mapPinsContainer) return;
    mapPinsContainer.innerHTML = "";

    const filtered = getFilteredReports();

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
        selectReport(report);
      });

      mapPinsContainer.appendChild(pinEl);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  // Render Incident Cards Grid
  function renderIncidentCards() {
    if (!incidentCardsContainer) return;
    incidentCardsContainer.innerHTML = "";

    const filtered = getFilteredReports();
    if (feedCountEl) feedCountEl.textContent = filtered.length;
    if (cardsCountPill) cardsCountPill.textContent = `${filtered.length} incidents`;

    if (filtered.length === 0) {
      incidentCardsContainer.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 3rem 1.5rem; text-align: center; background: #0f172a; border: 1px dashed #1e293b; border-radius: 1rem; color: #94a3b8;">
          <p style="font-size: 0.95rem; font-weight: 600;">No hazards match your filter query.</p>
          <p style="font-size: 0.75rem; margin-top: 0.35rem; color: #64748b;">Try adjusting your search criteria or selecting 'All Cebu City Barangays'.</p>
        </div>
      `;
      return;
    }

    filtered.forEach(report => {
      const sevConfig = getSeverityConfig(report.severity);
      const statusConfig = getStatusConfig(report.status);

      const card = document.createElement("div");
      card.style.cssText = `
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 1rem;
        padding: 1.15rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        cursor: pointer;
        transition: all 0.2s ease;
      `;
      card.addEventListener("mouseenter", () => {
        card.style.borderColor = "#f59e0b";
        card.style.transform = "translateY(-2px)";
      });
      card.addEventListener("mouseleave", () => {
        card.style.borderColor = "#1e293b";
        card.style.transform = "translateY(0)";
      });

      card.innerHTML = `
        <div>
          <!-- Header Meta -->
          <div style="display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.6rem;">
            <div style="display: flex; align-items: center; gap: 0.45rem;">
              <span style="font-family: var(--font-mono); font-size: 0.75rem; font-weight: 700; color: #fbbf24;">${report.ticketNumber}</span>
              <span class="badge-pill ${sevConfig.badgeClass}" style="font-size: 0.62rem; padding: 0.1rem 0.4rem;">${sevConfig.label}</span>
            </div>
            <span class="badge-pill ${statusConfig.badgeClass}" style="font-size: 0.65rem; padding: 0.1rem 0.45rem;">${statusConfig.label}</span>
          </div>

          <!-- Title -->
          <h3 style="font-size: 0.95rem; font-weight: 700; color: #ffffff; line-height: 1.35; margin-bottom: 0.35rem; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
            ${report.title}
          </h3>

          <!-- Address -->
          <p style="font-size: 0.75rem; color: #94a3b8; display: flex; align-items: center; gap: 0.35rem;">
            <i data-lucide="map-pin" style="width: 14px; height: 14px; color: #fbbf24; flex-shrink: 0;"></i>
            <span>${report.address}</span>
          </p>

          <!-- AI Telemetry Snippet Box -->
          <div style="margin-top: 0.85rem; padding: 0.65rem; border-radius: 0.65rem; background: rgba(2, 6, 23, 0.6); border: 1px solid #1e293b; font-size: 0.72rem; display: flex; flex-direction: column; gap: 0.25rem;">
            <div style="display: flex; justify-content: space-between;">
              <span style="color: #64748b;">Clearance Sag:</span>
              <span style="color: #f43f5e; font-weight: 600;">${(report.aiAnalysis?.cableSagClearance || "3.2m above road").split("(")[0]}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
              <span style="color: #64748b;">AI Confidence:</span>
              <span style="color: #34d399; font-weight: 700; font-family: var(--font-mono);">${report.aiAnalysis?.confidence || 95.4}%</span>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid #1e293b; display: flex; align-items: center; justify-content: space-between; font-size: 0.72rem; color: #64748b;">
          <span>Reported ${report.reportedAt}</span>
          <span style="color: #fbbf24; font-weight: 600; display: inline-flex; align-items: center; gap: 0.25rem;">
            <span>Inspect Telemetry</span>
            <i data-lucide="chevron-right" style="width: 13px; height: 13px;"></i>
          </span>
        </div>
      `;

      card.addEventListener("click", () => {
        openDetailModal(report);
      });

      incidentCardsContainer.appendChild(card);
    });

    if (window.lucide) window.lucide.createIcons();
  }

  // Select Report on Map
  function selectReport(report) {
    currentSelectedReport = report;
    renderMapPins();

    if (previewCard && report) {
      previewCard.style.display = "flex";
      if (previewImage) previewImage.src = report.imageUrl;
      if (previewTicket) previewTicket.textContent = report.ticketNumber;
      if (previewBarangay) previewBarangay.textContent = `Brgy. ${report.barangay}`;
      if (previewTitle) previewTitle.textContent = report.title;
      if (previewAddress) previewAddress.textContent = report.address;

      const sevConfig = getSeverityConfig(report.severity);
      if (previewSeverityBadge) {
        previewSeverityBadge.className = `badge-pill ${sevConfig.badgeClass}`;
        previewSeverityBadge.textContent = sevConfig.label;
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
    if (detailImage) detailImage.src = report.imageUrl;

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
        item.style.cssText = "display: flex; justify-content: space-between; align-items: center; color: #cbd5e1;";
        item.innerHTML = `
          <span><strong>${r.agency}</strong> (${r.department || 'Dispatch'})</span>
          <span style="color: #34d399; font-weight: 600;">✓ ${r.status || 'Delivered'}</span>
        `;
        detailRecipientsList.appendChild(item);
      });
    }

    detailModal.classList.add("open");
    if (window.lucide) window.lucide.createIcons();
  }

  function closeDetailModal() {
    if (detailModal) detailModal.classList.remove("open");
  }

  if (closeDetailModalBtn) closeDetailModalBtn.addEventListener("click", closeDetailModal);
  if (closeDetailFooterBtn) closeDetailFooterBtn.addEventListener("click", closeDetailModal);

  // Status Toggle
  if (toggleStatusBtn) {
    toggleStatusBtn.addEventListener("click", async () => {
      if (!currentSelectedReport) return;
      const nextStatus = currentSelectedReport.status === "resolved" ? "dispatched" : "resolved";
      
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
          
          // Re-render
          openDetailModal(currentSelectedReport);
          renderMapPins();
          renderIncidentCards();
          updateStats();
        }
      } catch (err) {
        console.error("Status toggle error:", err);
      }
    });
  }

  function updateStats() {
    const total = reports.length;
    const critical = reports.filter(r => r.severity === "critical").length;
    const dispatched = reports.filter(r => r.status === "dispatched").length;
    const resolved = reports.filter(r => r.status === "resolved").length;

    const elTotal = document.getElementById("stat-total");
    const elCrit = document.getElementById("stat-critical");
    const elDisp = document.getElementById("stat-dispatched");
    const elRes = document.getElementById("stat-resolved");

    if (elTotal) elTotal.textContent = total;
    if (elCrit) elCrit.textContent = critical;
    if (elDisp) elDisp.textContent = dispatched;
    if (elRes) elRes.textContent = resolved;
  }

  // Report Wizard Logic
  let selectedPresetIndex = 0;
  let customUploadedImage = null;

  function openReportModal() {
    if (!reportModal) return;
    setWizardStep("input");
    reportModal.classList.add("open");
  }

  function closeReportModal() {
    if (!reportModal) return;
    reportModal.classList.remove("open");
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

  // Preset Selection
  const presetBtns = document.querySelectorAll(".preset-card-btn");
  presetBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      presetBtns.forEach(b => {
        b.style.borderColor = "#1e293b";
        b.style.background = "#0b1120";
      });
      btn.style.borderColor = "#f59e0b";
      btn.style.background = "rgba(245, 158, 11, 0.08)";

      const idx = parseInt(btn.getAttribute("data-preset-index"), 10);
      selectedPresetIndex = idx;
      customUploadedImage = null;

      const p = presets[idx];
      if (p) {
        if (wizardPhotoPreview) wizardPhotoPreview.src = p.imageUrl;
        if (wizardPhotoBadge) wizardPhotoBadge.textContent = `Brgy. ${p.barangay}`;
        if (wizardTitleInput) wizardTitleInput.value = p.title;
        if (wizardBarangaySelect) wizardBarangaySelect.value = p.barangay;
        if (wizardAddressInput) wizardAddressInput.value = p.address;
      }
    });
  });

  // Custom File Upload Handler
  if (wizardCustomFile) {
    wizardCustomFile.addEventListener("change", e => {
      const file = e.target.files?.[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = () => {
          customUploadedImage = reader.result;
          if (wizardPhotoPreview) wizardPhotoPreview.src = customUploadedImage;
          const brgy = wizardBarangaySelect ? wizardBarangaySelect.value : "Tisa";
          if (wizardPhotoBadge) wizardPhotoBadge.textContent = `Brgy. ${brgy} (Custom Upload)`;
        };
        reader.readAsDataURL(file);
      }
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
          setTimeout(() => {
            const p = presets[selectedPresetIndex] || presets[0];
            if (resConfidence) resConfidence.textContent = `${p.confidence || 96.8}%`;
            if (resSag) resSag.textContent = p.sagClearance || "2.9m clearance";
            setWizardStep("result");
          }, 350);
        }
      }, 400);
    });
  }

  // Confirm Dispatch & Create Report API
  if (confirmDispatchBtn) {
    confirmDispatchBtn.addEventListener("click", async () => {
      confirmDispatchBtn.disabled = true;
      confirmDispatchBtn.innerHTML = `<span>Dispatching...</span>`;

      const p = presets[selectedPresetIndex] || presets[0];
      const title = wizardTitleInput ? wizardTitleInput.value : p.title;
      const barangay = wizardBarangaySelect ? wizardBarangaySelect.value : p.barangay;
      const address = wizardAddressInput ? wizardAddressInput.value : p.address;
      const imageUrl = customUploadedImage || p.imageUrl;

      let gps = { lat: 10.2982, lng: 123.8741 };
      if (barangay === "Buhisan") gps = { lat: 10.2891, lng: 123.8633 };
      else if (barangay === "Lahug") gps = { lat: 10.3298, lng: 123.9056 };
      else if (barangay === "Guadalupe") gps = { lat: 10.3152, lng: 123.8821 };

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
            severity: p.severity || "critical",
            hazardType: p.hazardType || "sagging_cable",
            imageUrl: imageUrl,
            confidence: p.confidence || 96.4,
            sagClearance: p.sagClearance || "2.9m clearance",
            wireDensity: p.wireDensity || "High bundle density",
            components: p.components || ["Sagging cable", "Overgrown spaghetti loop"],
          }),
        });

        if (response.ok) {
          const resData = await response.json();
          const newRep = resData.report;

          reports.unshift(newRep);
          closeReportModal();
          confirmDispatchBtn.disabled = false;
          confirmDispatchBtn.innerHTML = `<span>Submit & Dispatch Report</span>`;

          // Refresh UI
          renderMapPins();
          renderIncidentCards();
          updateStats();
          selectReport(newRep);
          openDetailModal(newRep);
        }
      } catch (err) {
        console.error("Dispatch error:", err);
        confirmDispatchBtn.disabled = false;
        confirmDispatchBtn.innerHTML = `<span>Submit & Dispatch Report</span>`;
      }
    });
  }

  // Filter Listeners
  if (searchInput) searchInput.addEventListener("input", () => { renderMapPins(); renderIncidentCards(); });
  if (barangaySelect) barangaySelect.addEventListener("change", () => { renderMapPins(); renderIncidentCards(); });
  if (severitySelect) severitySelect.addEventListener("change", () => { renderMapPins(); renderIncidentCards(); });

  // View Switcher Tabs
  if (viewMapBtn && viewListBtn) {
    viewMapBtn.addEventListener("click", () => {
      activeTab = "map";
      viewMapBtn.style.background = "#f59e0b";
      viewMapBtn.style.color = "#020617";
      viewListBtn.style.background = "transparent";
      viewListBtn.style.color = "#94a3b8";

      if (mapViewSection) mapViewSection.style.display = "flex";
      if (feedViewSection) feedViewSection.style.display = "flex";
      renderMapPins();
    });

    viewListBtn.addEventListener("click", () => {
      activeTab = "feed";
      viewListBtn.style.background = "#f59e0b";
      viewListBtn.style.color = "#020617";
      viewMapBtn.style.background = "transparent";
      viewMapBtn.style.color = "#94a3b8";

      if (feedViewSection) {
        feedViewSection.scrollIntoView({ behavior: "smooth" });
      }
    });
  }

  // Initial render
  renderMapPins();
  renderIncidentCards();
  if (reports.length > 0) {
    selectReport(reports[0]);
  }
});
