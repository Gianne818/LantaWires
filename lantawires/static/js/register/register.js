// LantaWires Register Client Script

document.addEventListener("DOMContentLoaded", () => {
  const autofillBtn = document.getElementById("register-autofill-btn");
  const nameInput = document.getElementById("register-name-input");
  const phoneInput = document.getElementById("register-phone-input");
  const emailInput = document.getElementById("register-email-input");
  const barangaySelect = document.getElementById("register-barangay-select");
  const passwordInput = document.getElementById("register-password-input");
  const confirmPasswordInput = document.getElementById("register-confirm-password-input");
  const togglePassBtn = document.getElementById("toggle-reg-password-btn");
  const registerForm = document.getElementById("register-form");
  const submitBtn = document.getElementById("register-submit-btn");

  // Autofill sample registration data
  if (autofillBtn) {
    autofillBtn.addEventListener("click", () => {
      if (nameInput) nameInput.value = "Gianne Cruz";
      if (phoneInput) phoneInput.value = "+63 917 554 8921";
      if (emailInput) emailInput.value = "gianne@cebucity.ph";
      if (barangaySelect) barangaySelect.value = "Tisa";
      if (passwordInput) passwordInput.value = "cebuwirehazard2026";
      if (confirmPasswordInput) confirmPasswordInput.value = "cebuwirehazard2026";

      // Flash highlight
      [nameInput, phoneInput, emailInput, passwordInput, confirmPasswordInput].forEach(el => {
        if (!el) return;
        el.style.borderColor = "#fbbf24";
        el.style.boxShadow = "0 0 0 3px rgba(245, 158, 11, 0.3)";
        setTimeout(() => {
          el.style.borderColor = "";
          el.style.boxShadow = "";
        }, 600);
      });
    });
  }

  // Password visibility toggle
  if (togglePassBtn && passwordInput) {
    togglePassBtn.addEventListener("click", () => {
      const isPassword = passwordInput.type === "password";
      passwordInput.type = isPassword ? "text" : "password";
      if (confirmPasswordInput) {
        confirmPasswordInput.type = isPassword ? "text" : "password";
      }
      
      togglePassBtn.innerHTML = isPassword 
        ? '<i data-lucide="eye-off" style="width: 16px; height: 16px;"></i>'
        : '<i data-lucide="eye" style="width: 16px; height: 16px;"></i>';
      if (window.lucide) window.lucide.createIcons();
    });
  }

  // Submit validation and spinner
  if (registerForm && submitBtn) {
    registerForm.addEventListener("submit", (e) => {
      if (passwordInput.value !== confirmPasswordInput.value) {
        e.preventDefault();
        alert("Password confirmation does not match.");
        confirmPasswordInput.focus();
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <div style="width: 18px; height: 18px; border: 2px solid #020617; border-top-color: transparent; border-radius: 9999px; animation: spin 0.6s linear infinite;"></div>
        <span>Creating Account...</span>
      `;
    });
  }
});
