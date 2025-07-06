// Enhanced Offline/CDN failure detector with immediate feedback
(function () {
  let cdnFailures = 0;
  let cdnSuccesses = 0;
  let statusShown = false;

  function createStatusIndicator() {
    if (statusShown) return;
    statusShown = true;

    const indicator = document.createElement("div");
    indicator.id = "cdn-status-indicator";
    indicator.innerHTML = `
            <div style="
                position: fixed;
                top: 10px;
                right: 10px;
                background: linear-gradient(135deg, #48bb78, #38a169);
                color: white;
                padding: 8px 16px;
                border-radius: 25px;
                font-family: Arial, sans-serif;
                font-size: 12px;
                z-index: 10000;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 8px;
            " onclick="this.parentElement.remove()">
                <span id="status-icon">🌐</span>
                <span id="status-text">وضع محلي نشط</span>
                <span style="opacity: 0.7; font-size: 10px;">×</span>
            </div>
        `;

    document.body.appendChild(indicator);

    // Auto-hide after 15 seconds
    setTimeout(() => {
      const existing = document.getElementById("cdn-status-indicator");
      if (existing) {
        existing.style.opacity = "0";
        setTimeout(() => existing.remove(), 500);
      }
    }, 15000);
  }

  function updateStatus(type) {
    const indicator = document.getElementById("cdn-status-indicator");
    if (!indicator) return;

    const icon = indicator.querySelector("#status-icon");
    const text = indicator.querySelector("#status-text");
    const container = indicator.firstElementChild;

    if (type === "offline") {
      icon.textContent = "📶";
      text.textContent = "وضع محلي فقط";
      container.style.background = "linear-gradient(135deg, #ff6b6b, #ee5a52)";
    } else if (type === "mixed") {
      icon.textContent = "⚡";
      text.textContent = "وضع محلي محسن";
      container.style.background = "linear-gradient(135deg, #4299e1, #3182ce)";
    } else if (type === "online") {
      icon.textContent = "✅";
      text.textContent = "اتصال كامل";
      container.style.background = "linear-gradient(135deg, #48bb78, #38a169)";
    }
  }

  function trackCDNStatus(success, url) {
    if (success) {
      cdnSuccesses++;
    
    } else {
      cdnFailures++;
   
    }

    // Update status based on results
    if (cdnFailures > 0 && cdnSuccesses === 0) {
      updateStatus("offline");
    } else if (cdnFailures > 0 && cdnSuccesses > 0) {
      updateStatus("mixed");
    } else if (cdnSuccesses > 0) {
      updateStatus("online");
    }
  }

  // Initialize status indicator immediately
  setTimeout(createStatusIndicator, 500);

  // Override the global loadCDNResource function to track success/failure
  window.trackCDNStatus = trackCDNStatus;

  // Enhanced error detection
  const originalError = console.error;
  console.error = function (...args) {
    const errorMessage = args.join(" ");
    if (
      errorMessage.includes("net::ERR_ABORTED") &&
      errorMessage.includes("503")
    ) {
      trackCDNStatus(false, "CDN Service");
    }
    originalError.apply(console, args);
  };

  // Network status monitoring
  if ("navigator" in window && "onLine" in navigator) {
    function checkNetworkStatus() {
      if (!navigator.onLine) {
        updateStatus("offline");
      }
    }

    window.addEventListener("online", () => updateStatus("mixed"));
    window.addEventListener("offline", () => updateStatus("offline"));

    // Initial network check
    if (!navigator.onLine) {
      setTimeout(() => updateStatus("offline"), 1000);
    }
  }

  // Listen for successful resource loads
  document.addEventListener("DOMContentLoaded", function () {
    // Monitor all script and link elements
    document
      .querySelectorAll('script[src], link[rel="stylesheet"]')
      .forEach((element) => {
        element.addEventListener("load", function () {
          if (
            this.src &&
            (this.src.includes("cdn") || this.src.includes("googleapis"))
          ) {
            trackCDNStatus(true, this.src);
          }
          if (
            this.href &&
            (this.href.includes("cdn") || this.href.includes("googleapis"))
          ) {
            trackCDNStatus(true, this.href);
          }
        });

        element.addEventListener("error", function () {
          if (
            this.src &&
            (this.src.includes("cdn") || this.src.includes("googleapis"))
          ) {
            trackCDNStatus(false, this.src);
          }
          if (
            this.href &&
            (this.href.includes("cdn") || this.href.includes("googleapis"))
          ) {
            trackCDNStatus(false, this.href);
          }
        });
      });
  });

 
})();
