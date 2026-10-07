/**
 * User Settings Client JavaScript
 * CSIT327 Vertical Slicing Implementation
 */
document.addEventListener("DOMContentLoaded", () => {
  const toggleSwitches = document.querySelectorAll(".settings-switch-input");

  toggleSwitches.forEach(sw => {
    sw.addEventListener("change", (e) => {
      const parentCard = e.target.closest(".settings-row");
      if (parentCard) {
        parentCard.classList.toggle("setting-active", e.target.checked);
      }
      if (e.target.name === "dark_mode" || e.target.id === "setting-dark-mode") {
        var next = e.target.checked ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", next);
        try { localStorage.setItem("lw-theme", next); } catch (err) {}
      }
    });
  });
});
