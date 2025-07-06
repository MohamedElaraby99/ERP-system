// Client Type Selection
document.querySelectorAll("[data-client-type]").forEach((button) => {
  button.addEventListener("click", function () {
    document
      .querySelectorAll("[data-client-type]")
      .forEach((btn) => btn.classList.remove("active"));
    this.classList.add("active");
    document.getElementById("clientType").value =
      this.getAttribute("data-client-type");

    // Toggle fields visibility
    const companyFields = document.getElementById("companyFields");
    const individualFields = document.getElementById("individualFields");

    if (this.getAttribute("data-client-type") === "company") {
      companyFields.style.display = "block";
      individualFields.style.display = "none";
    } else {
      companyFields.style.display = "none";
      individualFields.style.display = "block";
    }
  });
});

// Initialize counters
function updateCounters() {
  fetch("/api/clients/stats")
    .then((response) => response.json())
    .then((data) => {
      document.getElementById("companiesCount").textContent =
        data.companies || 0;
      document.getElementById("individualsCount").textContent =
        data.individuals || 0;
      document.getElementById("totalCount").textContent = data.total || 0;
      document.getElementById("targetedCount").textContent = data.targeted || 0;
    })
    .catch((error) => console.error("Error fetching stats:", error));
}

// Load clients data
function loadClients() {
  fetch("/api/clients")
    .then((response) => response.json())
    .then((clients) => {
      const tableBody = document.getElementById("clientsTableBody");
      tableBody.innerHTML = "";

      clients.forEach((client) => {
        const row = document.createElement("tr");
        row.innerHTML = `
                    <td>${client.name}</td>
                    <td>
                        <span class="badge ${
                          client.type === "company" ? "bg-primary" : "bg-info"
                        }">
                            ${client.type === "company" ? "شركة" : "فرد"}
                        </span>
                    </td>
                    <td>
                        <span class="badge ${
                          client.status === "active"
                            ? "bg-success"
                            : "bg-warning"
                        }">
                            ${client.status === "active" ? "نشط" : "غير نشط"}
                        </span>
                    </td>
                    <td>${new Date(client.created_at).toLocaleDateString(
                      "ar-SA"
                    )}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary edit-client" data-id="${
                          client.id
                        }">
                            <span class="material-icons">edit</span>
                        </button>
                        <button class="btn btn-sm btn-outline-danger delete-client" data-id="${
                          client.id
                        }" onclick="confirmDelete(${client.id}, '${
          client.name
        }')">
                            <span class="material-icons">delete</span>
                        </button>
                    </td>
                `;
        tableBody.appendChild(row);
      });

      // Initialize tooltips
      const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
      );
      tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
      });
    })
    .catch((error) => console.error("Error loading clients:", error));
}

// Search functionality
const searchInput = document.getElementById("searchInput");
searchInput.addEventListener(
  "input",
  debounce(function () {
    const searchTerm = this.value.toLowerCase();
    const rows = document.querySelectorAll("#clientsTableBody tr");

    rows.forEach((row) => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(searchTerm) ? "" : "none";
    });
  }, 300)
);

// Debounce helper function
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func.apply(this, args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Export functionality
document.getElementById("exportBtn").addEventListener("click", function () {
  fetch("/api/clients/export")
    .then((response) => response.blob())
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "clients.xlsx";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    })
    .catch((error) => console.error("Error exporting clients:", error));
});

// Add client form submission
document
  .getElementById("addClientForm")
  .addEventListener("submit", function (e) {
    e.preventDefault();
    const formData = new FormData(this);

    fetch("/api/clients", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          bootstrap.Modal.getInstance(
            document.getElementById("addClientModal")
          ).hide();
          loadClients();
          updateCounters();
          showToast("success", "تم إضافة العميل بنجاح");
        } else {
          showToast("error", "حدث خطأ أثناء إضافة العميل");
        }
      })
      .catch((error) => {
        console.error("Error adding client:", error);
        showToast("error", "حدث خطأ أثناء إضافة العميل");
      });
  });

// Delete client confirmation
function confirmDelete(clientId, clientName) {
  if (!clientId) return;

  const modal = document.createElement("div");
  modal.className = "modal fade";
  modal.id = "deleteConfirmModal";
  modal.setAttribute("tabindex", "-1");
  modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">تأكيد الحذف</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <p>هل أنت متأكد من حذف العميل "${clientName}"؟</p>
                    <div class="alert alert-warning">
                        <span class="material-icons">warning</span>
                        هذا الإجراء لا يمكن التراجع عنه.
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                        <span class="material-icons">close</span> إلغاء
                    </button>
                    <button type="button" class="btn btn-danger" onclick="deleteClient(${clientId})">
                        <span class="material-icons">delete_forever</span> حذف
                    </button>
                </div>
            </div>
        </div>
    `;

  document.body.appendChild(modal);
  const modalInstance = new bootstrap.Modal(modal);
  modalInstance.show();

  modal.addEventListener("hidden.bs.modal", function () {
    modal.remove();
  });
}

// Delete client
function deleteClient(clientId) {
  if (!clientId) return;

  fetch(`/api/clients/${clientId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        bootstrap.Modal.getInstance(
          document.getElementById("deleteConfirmModal")
        ).hide();
        loadClients();
        updateCounters();
        showToast("success", "تم حذف العميل بنجاح");
      } else {
        showToast("error", data.message || "حدث خطأ أثناء حذف العميل");
      }
    })
    .catch((error) => {
      console.error("Error deleting client:", error);
      showToast("error", "حدث خطأ أثناء حذف العميل");
    });
}

// Toast notifications
function showToast(type, message) {
  const toast = document.createElement("div");
  toast.className = "toast align-items-center text-white border-0";
  toast.style.position = "fixed";
  toast.style.bottom = "1rem";
  toast.style.right = "1rem";
  toast.style.zIndex = "9999";
  toast.style.minWidth = "250px";

  if (type === "success") {
    toast.style.backgroundColor = "#48BB78";
  } else if (type === "error") {
    toast.style.backgroundColor = "#F56565";
  }

  toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <span class="material-icons me-2">${
                  type === "success" ? "check_circle" : "error"
                }</span>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

  document.body.appendChild(toast);
  const toastInstance = new bootstrap.Toast(toast, { delay: 3000 });
  toastInstance.show();

  toast.addEventListener("hidden.bs.toast", function () {
    toast.remove();
  });
}

// Initialize page
document.addEventListener("DOMContentLoaded", function () {
  updateCounters();
  loadClients();
});
