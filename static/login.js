// Login form handling
document.addEventListener("DOMContentLoaded", function () {
  const loginForm = document.getElementById("loginForm");
  const loginButton = document.getElementById("loginButton");
  const alertContainer = document.getElementById("alertContainer");

  // Get CSRF token from meta tag
  function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]')?.content;
    if (!token) {
      console.error("CSRF token not found");
      return null;
    }
    return token;
  }

  // Show alert message
  function showAlert(message, type = "danger") {
    alertContainer.innerHTML = `
      <div class="alert alert-${type}" role="alert">
        ${message}
      </div>
    `;
    alertContainer.style.display = "block";
  }

  // Clear alert message
  function clearAlert() {
    alertContainer.innerHTML = "";
    alertContainer.style.display = "none";
  }

  // Handle form submission
  loginForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    clearAlert();

    // Get form data
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const rememberMe = document.getElementById("rememberMe").checked;

    // Basic validation
    if (!email || !password) {
      showAlert("الرجاء إدخال البريد الإلكتروني وكلمة المرور");
      return;
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      showAlert("الرجاء إدخال بريد إلكتروني صحيح");
      return;
    }

    // Show loading state
    loginButton.disabled = true;
    loginButton.classList.add("loading");

    try {
      // Get CSRF token
      const csrfToken = getCSRFToken();
      if (!csrfToken) {
        throw new Error("CSRF token not found");
      }

      // Make login request
      const response = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        credentials: "include",
        body: JSON.stringify({
          email: email,
          password: password,
          remember_me: rememberMe,
        }),
      });

      // Parse response
      const data = await response.json();

      // Handle response
      if (response.ok && data.success) {
        // Store tokens
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);

        // Store user info
        localStorage.setItem("user", JSON.stringify(data.user));

        // Update CSRF token if provided in response
        const newCSRFToken = response.headers.get("X-CSRFToken");
        if (newCSRFToken) {
          document.querySelector('meta[name="csrf-token"]').content =
            newCSRFToken;
        }

        // Redirect to dashboard
        window.location.href = "/dashboard";
      } else {
        // Show error message
        showAlert(data.message || "حدث خطأ في تسجيل الدخول");
      }
    } catch (error) {
      console.error("Login error:", error);
      showAlert("حدث خطأ في الاتصال بالخادم. الرجاء المحاولة لاحقاً.");
    } finally {
      // Reset loading state
      loginButton.disabled = false;
      loginButton.classList.remove("loading");
    }
  });
});
