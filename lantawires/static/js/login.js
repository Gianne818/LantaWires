// LantaWires Login Client Script

document.addEventListener("DOMContentLoaded", () => {
  const autofillBtn = document.getElementById("login-autofill-btn");
  const emailInput = document.getElementById("login-email-input");
  const passwordInput = document.getElementById("login-password-input");
  const togglePassBtn = document.getElementById("toggle-password-btn");
  const loginForm = document.getElementById("login-form");
  const submitBtn = document.getElementById("login-submit-btn");

  // Autofill sample credentials
  if (autofillBtn) {
    autofillBtn.addEventListener("click", () => {
      if (emailInput) emailInput.value = "gianne@cebucity.ph";
      if (passwordInput) passwordInput.value = "cebuwirehazard2026";
      
      // Flash input effect
      [emailInput, passwordInput].forEach(el => {
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
      
      // Update icon
      togglePassBtn.innerHTML = isPassword 
        ? '<i data-lucide="eye-off" style="width: 16px; height: 16px;"></i>'
        : '<i data-lucide="eye" style="width: 16px; height: 16px;"></i>';
      if (window.lucide) window.lucide.createIcons();
    });
  }

  // Form submission loading indicator
  if (loginForm && submitBtn) {
    loginForm.addEventListener("submit", () => {
      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <div style="width: 18px; height: 18px; border: 2px solid #020617; border-top-color: transparent; border-radius: 9999px; animation: spin 0.6s linear infinite;"></div>
        <span>Logging in...</span>
      `;
    });
  }
});

// Dynamic spinner animation
const styleSheet = document.createElement("style");
styleSheet.innerText = `@keyframes spin { to { transform: rotate(360deg); } }`;
document.head.appendChild(styleSheet);
