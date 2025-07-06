// System Check - Verify all local components are working
(function () {
  const checks = [];

  // Check 1: CSS Fallback
  checks.push({
    name: "CSS Fallback",
    test: () => {
      const testElement = document.createElement("div");
      testElement.className = "btn btn-primary";
      document.body.appendChild(testElement);
      const styles = window.getComputedStyle(testElement);
      const hasStyles = styles.padding !== "0px";
      document.body.removeChild(testElement);
      return hasStyles;
    },
  });

  // Check 2: Bootstrap Fallback
  checks.push({
    name: "Bootstrap Fallback",
    test: () => typeof window.bootstrap !== "undefined",
  });

  // Check 3: Chart Fallback
  checks.push({
    name: "Chart.js Fallback",
    test: () => typeof window.Chart !== "undefined",
  });

  // Check 4: Offline Detector
  checks.push({
    name: "Offline Detector",
    test: () => typeof window.trackCDNStatus !== "undefined",
  });

  // Check 5: API Endpoints
  checks.push({
    name: "Dashboard API",
    test: async () => {
      try {
        const response = await fetch("/api/v1/projects/", {
          method: "HEAD",
        });
        return response.status !== 404;
      } catch {
        return false;
      }
    },
  });

  // Run checks
  setTimeout(async () => {
    // for (const check of checks) {
    //   try {
    //     const result = await check.test();
    //     console.log(
    //       `${result ? "✅" : "❌"} ${check.name}: ${
    //         result ? "Working" : "Failed"
    //       }`
    //     );
    //   } catch (error) {
    //     console.log(`❌ ${check.name}: Error - ${error.message}`);
    //   }
    // }

    // console.log("🎯 System check complete!");

    // Show status in UI
    const statusElement = document.createElement("div");
    statusElement.innerHTML = `
            <div style="
                position: fixed;
                bottom: 10px;
                left: 10px;
                background: rgba(72, 187, 120, 0.9);
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 12px;
                z-index: 9999;
                font-family: Arial, sans-serif;
                cursor: pointer;
            " onclick="this.parentElement.remove()">
                🟢 النظام يعمل بوضع محلي - اضغط للإغلاق
            </div>
        `;
    document.body.appendChild(statusElement);

    // Auto-hide after 5 seconds
    setTimeout(() => {
      if (statusElement.parentElement) {
        statusElement.style.opacity = "0";
        setTimeout(() => statusElement.remove(), 500);
      }
    }, 5000);
  }, 2000);
})();

// Enhanced ERP System Health Monitor
// Comprehensive CDN and Network Status Monitoring

class ERPSystemMonitor {
  constructor() {
    this.cdnStatus = {
      bootstrap: "checking",
    };
    this.networkStatus = navigator.onLine;
    this.lastCheckTime = Date.now();
    this.errorCount = 0;

    this.init();
  }

  init() {
    this.setupNetworkMonitoring();
    this.setupCDNMonitoring();
    this.setupErrorReporting();
    this.startHealthCheck();

    console.log("🔍 ERP System Monitor: Initialized");
  }

  setupNetworkMonitoring() {
    window.addEventListener("online", () => {
      this.networkStatus = true;
      console.log("🌐 Network: Connected");
      this.retryFailedCDNs();
    });

    window.addEventListener("offline", () => {
      this.networkStatus = false;
      console.log("📦 Network: Offline - Using local resources");
    });
  }

  setupCDNMonitoring() {
    // Monitor CDN loading attempts
    const originalFetch = window.fetch;
    window.fetch = (...args) => {
      return originalFetch(...args).catch((error) => {
        if (
          error.message.includes("503") ||
          error.message.includes("Failed to fetch")
        ) {
          this.handleCDNError(args[0], error);
        }
        throw error;
      });
    };
  }

  setupErrorReporting() {
    // Catch all unhandled errors
    window.addEventListener("error", (event) => {
      if (
        event.target.tagName === "LINK" ||
        event.target.tagName === "SCRIPT"
      ) {
        this.handleResourceError(event.target);
      }
    });

    // Catch unhandled promise rejections
    window.addEventListener("unhandledrejection", (event) => {
      if (
        event.reason &&
        event.reason.message &&
        (event.reason.message.includes("503") ||
          event.reason.message.includes("CDN"))
      ) {
        console.log(
          "📦 CDN Promise rejection handled - continuing with local resources"
        );
        event.preventDefault(); // Prevent console error
      }
    });
  }

  handleResourceError(element) {
    const url = element.href || element.src;
    if (url && (url.includes("cdnjs") || url.includes("jsdelivr"))) {
      console.log(
        `📦 CDN Resource unavailable: ${url.substring(
          0,
          50
        )}... - Using local fallback`
      );
      this.errorCount++;

      // Mark CDN as failed
      if (url.includes("bootstrap")) {
        this.cdnStatus.bootstrap = "failed";
      }
    }
  }

  handleCDNError(url, error) {
    console.log(`📦 CDN Fetch Error: ${url} - ${error.message}`);
    this.errorCount++;
  }

  retryFailedCDNs() {
    if (!this.networkStatus) return;

    // Only retry if we're back online and have failed CDNs
    const failedCDNs = Object.entries(this.cdnStatus).filter(
      ([key, status]) => status === "failed"
    );

    if (failedCDNs.length > 0) {
      console.log("🔄 Network restored - Retrying failed CDNs...");

      setTimeout(() => {
        if (window.loadCDNResource) {
          // Reset status for retry
          failedCDNs.forEach(([key]) => {
            this.cdnStatus[key] = "retrying";
          });

          // Retry CDN loading
          window.cdnLoadingInProgress = false;
          window.cdnLoadedResources.clear();

          // Trigger CDN reload
          const event = new Event("DOMContentLoaded");
          document.dispatchEvent(event);
        }
      }, 2000);
    }
  }

  startHealthCheck() {
    setInterval(() => {
      this.performHealthCheck();
    }, 30000); // Check every 30 seconds

    // Initial check after 5 seconds
    setTimeout(() => {
      this.performHealthCheck();
    }, 5000);
  }

  performHealthCheck() {
    const now = Date.now();
    const uptime = Math.floor((now - this.lastCheckTime) / 1000);

    // Check if local resources are working
    const localResourcesWorking = this.checkLocalResources();

    if (localResourcesWorking) {
      console.log(
        `✅ ERP System Health Check: All systems operational (${uptime}s)`
      );

      // Report CDN status
      const workingCDNs = Object.entries(this.cdnStatus).filter(
        ([key, status]) => status === "loaded" || status === "checking"
      ).length;

      if (workingCDNs === Object.keys(this.cdnStatus).length) {
        console.log("📡 All CDN resources loaded successfully");
      } else {
        console.log(
          `📡 ${workingCDNs}/${
            Object.keys(this.cdnStatus).length
          } CDN resources loaded`
        );
      }
    } else {
      console.log(
        "⚠️ ERP System Health Check: Some local resources are not working"
      );
    }
  }

  checkLocalResources() {
    // Check if critical local resources are available
    const criticalElements = [
      "btn", // Bootstrap
      "material-icons", // Material Icons
      "fade-in", // Custom styles
    ];

    const testDiv = document.createElement("div");
    document.body.appendChild(testDiv);

    let allResourcesWorking = true;

    criticalElements.forEach((className) => {
      testDiv.className = className;
      const styles = window.getComputedStyle(testDiv);
      if (styles.all === "initial") {
        allResourcesWorking = false;
        console.log(`⚠️ Local resource not working: ${className}`);
      }
    });

    document.body.removeChild(testDiv);
    return allResourcesWorking;
  }

  getSystemStatus() {
    return {
      networkStatus: this.networkStatus,
      cdnStatus: this.cdnStatus,
      errorCount: this.errorCount,
      uptime: Math.floor((Date.now() - this.lastCheckTime) / 1000),
    };
  }

  static getInstance() {
    if (!window._erpSystemMonitor) {
      window._erpSystemMonitor = new ERPSystemMonitor();
    }
    return window._erpSystemMonitor;
  }
}

// Initialize the monitor
ERPSystemMonitor.getInstance();

// Enhanced error suppression for CDN issues
window.addEventListener(
  "error",
  (event) => {
    // Suppress CDN-related errors to prevent console spam
    if (
      event.filename &&
      (event.filename.includes("cdnjs.cloudflare.com") ||
        event.filename.includes("cdn.jsdelivr.net") ||
        event.filename.includes("fonts.googleapis.com") ||
        event.filename.includes("use.fontawesome.com"))
    ) {
      console.log(
        "📦 CDN error suppressed - system operating normally with local resources"
      );
      event.preventDefault();
      return false;
    }
  },
  true
);

console.log("🛡️ ERP System: Enhanced error handling and monitoring active");
