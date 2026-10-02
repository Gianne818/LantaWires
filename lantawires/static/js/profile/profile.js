/**
 * Profile Feature Client JavaScript
 * CSIT327 Vertical Slicing Implementation
 */
document.addEventListener("DOMContentLoaded", () => {
  const avatarButtons = document.querySelectorAll(".avatar-preset-btn");
  const avatarInput = document.getElementById("profile-avatar-input");
  const avatarPreview = document.getElementById("profile-avatar-preview");

  if (avatarButtons.length > 0 && avatarInput && avatarPreview) {
    avatarButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        const selected = btn.getAttribute("data-avatar");
        avatarInput.value = selected;
        avatarPreview.textContent = selected;
        
        avatarButtons.forEach(b => b.classList.remove("selected-avatar"));
        btn.classList.add("selected-avatar");
      });
    });
  }
});
