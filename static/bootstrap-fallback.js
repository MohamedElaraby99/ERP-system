/**
 * Bootstrap Fallback JavaScript
 * Provides basic Bootstrap functionality when CDN is unavailable
 */

(function () {
  "use strict";

  // Check if Bootstrap is already loaded
  if (window.bootstrap || window.Bootstrap) {
    console.log("Bootstrap CDN loaded successfully");
    return;
  }

  console.log("Bootstrap CDN failed, loading fallback functionality");

  // Basic Modal Implementation
  class Modal {
    constructor(element, options = {}) {
      this.element =
        typeof element === "string" ? document.querySelector(element) : element;
      this.options = {
        backdrop: true,
        keyboard: true,
        focus: true,
        show: true,
        ...options,
      };
      this.isShown = false;
      this.backdrop = null;

      if (this.element) {
        this.init();
      }
    }

    init() {
      this.element.style.display = "none";
      this.element.style.position = "fixed";
      this.element.style.top = "0";
      this.element.style.left = "0";
      this.element.style.zIndex = "1050";
      this.element.style.width = "100%";
      this.element.style.height = "100%";
      this.element.style.overflow = "hidden";

      this.addEventListeners();
    }

    addEventListeners() {
      const closeButtons = this.element.querySelectorAll(
        '[data-bs-dismiss="modal"], [data-dismiss="modal"]'
      );
      closeButtons.forEach((btn) => {
        btn.addEventListener("click", () => this.hide());
      });

      this.element.addEventListener("click", (e) => {
        if (e.target === this.element && this.options.backdrop) {
          this.hide();
        }
      });

      if (this.options.keyboard) {
        document.addEventListener("keydown", (e) => {
          if (e.key === "Escape" && this.isShown) {
            this.hide();
          }
        });
      }
    }

    show() {
      if (this.isShown) return;

      this.isShown = true;
      document.body.style.overflow = "hidden";

      if (this.options.backdrop) {
        this.backdrop = document.createElement("div");
        this.backdrop.className = "modal-backdrop";
        this.backdrop.style.cssText = `
          position: fixed;
          top: 0;
          left: 0;
          z-index: 1040;
          width: 100vw;
          height: 100vh;
          background-color: rgba(0, 0, 0, 0.5);
        `;
        document.body.appendChild(this.backdrop);
      }

      this.element.style.display = "block";

      const dialog = this.element.querySelector(".modal-dialog");
      if (dialog) {
        dialog.style.cssText = `
          position: relative;
          width: auto;
          margin: 1.75rem auto;
          max-width: 500px;
          pointer-events: none;
        `;

        const content = dialog.querySelector(".modal-content");
        if (content) {
          content.style.cssText = `
            position: relative;
            display: flex;
            flex-direction: column;
            width: 100%;
            pointer-events: auto;
            background-color: #fff;
            border: 1px solid rgba(0,0,0,.2);
            border-radius: 0.5rem;
            outline: 0;
          `;
        }
      }

      setTimeout(() => {
        const shownEvent = new CustomEvent("shown.bs.modal", { bubbles: true });
        this.element.dispatchEvent(shownEvent);
      }, 150);
    }

    hide() {
      if (!this.isShown) return;

      this.isShown = false;
      this.element.style.display = "none";
      document.body.style.overflow = "";

      if (this.backdrop) {
        document.body.removeChild(this.backdrop);
        this.backdrop = null;
      }

      const hiddenEvent = new CustomEvent("hidden.bs.modal", { bubbles: true });
      this.element.dispatchEvent(hiddenEvent);
    }

    toggle() {
      return this.isShown ? this.hide() : this.show();
    }

    static getInstance(element) {
      const el =
        typeof element === "string" ? document.querySelector(element) : element;
      return el ? el._modalInstance : null;
    }

    static getOrCreateInstance(element, config) {
      return Modal.getInstance(element) || new Modal(element, config);
    }
  }

  // Basic Dropdown Implementation
  class Dropdown {
    constructor(element) {
      this.element = element;
      this.menu = element.nextElementSibling;
      this.isShown = false;
      this.init();
    }

    init() {
      this.element.addEventListener("click", (e) => {
        e.preventDefault();
        this.toggle();
      });

      // Close on outside click
      document.addEventListener("click", (e) => {
        if (!this.element.contains(e.target) && !this.menu.contains(e.target)) {
          this.hide();
        }
      });
    }

    show() {
      if (this.isShown) return;
      this.isShown = true;
      this.menu.style.display = "block";
      this.element.setAttribute("aria-expanded", "true");
    }

    hide() {
      if (!this.isShown) return;
      this.isShown = false;
      this.menu.style.display = "none";
      this.element.setAttribute("aria-expanded", "false");
    }

    toggle() {
      return this.isShown ? this.hide() : this.show();
    }
  }

  // Basic Collapse Implementation
  class Collapse {
    constructor(element) {
      this.element = element;
      this.isShown = false;
      this.init();
    }

    init() {
      this.element.style.overflow = "hidden";
      this.element.style.transition = "height 0.35s ease";

      if (!this.element.classList.contains("show")) {
        this.element.style.height = "0px";
      }
    }

    show() {
      if (this.isShown) return;
      this.isShown = true;

      const height = this.element.scrollHeight;
      this.element.style.height = height + "px";
      this.element.classList.add("show");

      setTimeout(() => {
        this.element.style.height = "";
      }, 350);
    }

    hide() {
      if (!this.isShown) return;
      this.isShown = false;

      this.element.style.height = this.element.offsetHeight + "px";

      setTimeout(() => {
        this.element.style.height = "0px";
        this.element.classList.remove("show");
      }, 10);
    }

    toggle() {
      return this.isShown ? this.hide() : this.show();
    }
  }

  // Create bootstrap object
  window.bootstrap = {
    Modal: Modal,
    Dropdown: Dropdown,
    Collapse: Collapse,
  };

  // Initialize modal triggers
  document.addEventListener("click", function (e) {
    const trigger = e.target.closest(
      '[data-bs-toggle="modal"], [data-toggle="modal"]'
    );
    if (trigger) {
      e.preventDefault();
      const target =
        trigger.getAttribute("data-bs-target") ||
        trigger.getAttribute("data-target");
      if (target) {
        const modal = Modal.getOrCreateInstance(target);
        modal.show();
      }
    }

    // Dropdown triggers
    const dropdownTrigger = e.target.closest(
      '[data-bs-toggle="dropdown"], [data-toggle="dropdown"]'
    );
    if (dropdownTrigger) {
      e.preventDefault();
      if (!dropdownTrigger._dropdownInstance) {
        dropdownTrigger._dropdownInstance = new Dropdown(dropdownTrigger);
      }
      dropdownTrigger._dropdownInstance.toggle();
    }

    // Collapse triggers
    const collapseTrigger = e.target.closest(
      '[data-bs-toggle="collapse"], [data-toggle="collapse"]'
    );
    if (collapseTrigger) {
      e.preventDefault();
      const target =
        collapseTrigger.getAttribute("data-bs-target") ||
        collapseTrigger.getAttribute("data-target");
      if (target) {
        const collapseElement = document.querySelector(target);
        if (collapseElement && !collapseElement._collapseInstance) {
          collapseElement._collapseInstance = new Collapse(collapseElement);
        }
        if (collapseElement) {
          collapseElement._collapseInstance.toggle();
        }
      }
    }
  });

  // Handle modal instances
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".modal").forEach((modal) => {
      modal._modalInstance = new Modal(modal, { show: false });
    });
  });

  // Initialize tooltips and popovers (basic implementation)
  window.bootstrap.Tooltip = function () {
    return { dispose: function () {} };
  };
  window.bootstrap.Popover = function () {
    return { dispose: function () {} };
  };

  console.log("Bootstrap fallback initialized");
})();
