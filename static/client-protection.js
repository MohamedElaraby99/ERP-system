// Client Protection System
(function () {
  // Configuration
  const config = {
    protectionEnabled: true,
    maxDeletionsPerHour: 5,
    requireConfirmation: true,
    logActions: true,
  };

  // Deletion tracking with localStorage persistence
  const deletionAttempts = {
    count: parseInt(localStorage.getItem("deletionCount") || "0"),
    lastReset: parseInt(
      localStorage.getItem("lastReset") || Date.now().toString()
    ),
  };

  // Reset deletion counter every hour
  function checkAndResetCounter() {
    const now = Date.now();
    const hoursPassed = (now - deletionAttempts.lastReset) / 3600000;

    if (hoursPassed >= 1) {
      deletionAttempts.count = 0;
      deletionAttempts.lastReset = now;
      localStorage.setItem("deletionCount", "0");
      localStorage.setItem("lastReset", now.toString());
    }
  }

  // Check counter every minute
  setInterval(checkAndResetCounter, 60000);

  // Override the deleteClient function
  const originalDeleteClient = window.deleteClient;
  window.deleteClient = function (clientId) {
    if (!config.protectionEnabled) {
      return originalDeleteClient(clientId);
    }

    checkAndResetCounter();

    // Check deletion limits
    if (deletionAttempts.count >= config.maxDeletionsPerHour) {
      showProtectionMessage("تم تجاوز الحد الأقصى لعمليات الحذف في الساعة");
      return false;
    }

    // Increment deletion counter
    deletionAttempts.count++;
    localStorage.setItem("deletionCount", deletionAttempts.count.toString());

    // Proceed with deletion
    return originalDeleteClient(clientId);
  };

  // Protection message display with performance optimization
  const messageQueue = [];
  let isShowingMessage = false;

  function showProtectionMessage(message) {
    messageQueue.push(message);
    if (!isShowingMessage) {
      processMessageQueue();
    }
  }

  function processMessageQueue() {
    if (messageQueue.length === 0) {
      isShowingMessage = false;
      return;
    }

    isShowingMessage = true;
    const message = messageQueue.shift();

    const toast = document.createElement("div");
    toast.className = "toast align-items-center text-white border-0";
    Object.assign(toast.style, {
      position: "fixed",
      bottom: "1rem",
      right: "1rem",
      zIndex: "9999",
      minWidth: "300px",
      backgroundColor: "#E53E3E",
      transform: "translateY(100%)",
      transition: "transform 0.3s ease-out",
    });

    toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <span class="material-icons me-2">security</span>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

    document.body.appendChild(toast);

    // Force reflow
    toast.offsetHeight;

    // Animate in
    toast.style.transform = "translateY(0)";

    setTimeout(() => {
      // Animate out
      toast.style.transform = "translateY(100%)";
      setTimeout(() => {
        toast.remove();
        processMessageQueue();
      }, 300);
    }, 5000);
  }

  // Log protection events with throttling
  let lastLogTime = 0;
  const LOG_THROTTLE = 1000; // 1 second

  function logProtectionEvent(event) {
    if (!config.logActions) return;

    const now = Date.now();
    if (now - lastLogTime < LOG_THROTTLE) return;

    lastLogTime = now;
    const timestamp = new Date().toISOString();
    console.log(`[Client Protection] ${timestamp}: ${event}`);
  }

  // Initialize protection system
  function initProtection() {
    if (!window.deleteClient) return;

    // Store original function
    const originalDeleteClient = window.deleteClient;

    // Override with protected version
    window.deleteClient = function (clientId) {
      if (!config.protectionEnabled) {
        return originalDeleteClient(clientId);
      }

      checkAndResetCounter();

      // Check deletion limits
      if (deletionAttempts.count >= config.maxDeletionsPerHour) {
        showProtectionMessage("تم تجاوز الحد الأقصى لعمليات الحذف في الساعة");
        return false;
      }

      // Increment deletion counter
      deletionAttempts.count++;
      localStorage.setItem("deletionCount", deletionAttempts.count.toString());

      // Proceed with deletion
      return originalDeleteClient(clientId);
    };

    // Add event listeners with debouncing
    let clickTimeout;
    document.addEventListener(
      "click",
      function (e) {
        clearTimeout(clickTimeout);
        clickTimeout = setTimeout(() => {
          if (e.target.closest(".delete-client")) {
            logProtectionEvent("Delete attempt detected");
          }
        }, 300);
      },
      { passive: true }
    );

    let submitTimeout;
    document.addEventListener(
      "submit",
      function (e) {
        clearTimeout(submitTimeout);
        submitTimeout = setTimeout(() => {
          if (e.target.id === "deleteClientForm") {
            logProtectionEvent("Delete form submission detected");
          }
        }, 300);
      },
      { passive: true }
    );

    logProtectionEvent("Protection system initialized");
  }

  // Initialize on page load with delay
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () =>
      setTimeout(initProtection, 1000)
    );
  } else {
    setTimeout(initProtection, 1000);
  }
})();
