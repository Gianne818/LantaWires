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
        if (e.target.checked) {
          parentCard.classList.add("setting-active");
        } else {
          parentCard.classList.remove("setting-active");
        }
      }
    });
  });
});
