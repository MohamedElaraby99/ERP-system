// Projects Management System - Enhanced with Modern Features
class ProjectManager {
  constructor() {
    this.currentStep = 1;
    this.maxSteps = 3;
    this.projects = [];
    this.clients = [];
    this.filteredProjects = [];

    this.init();
  }

  init() {
    this.bindEvents();
    this.loadInitialData();
    this.initializeAnimations();
  }

  bindEvents() {
    // Project type selector
    document.querySelectorAll(".type-option").forEach((option) => {
      option.addEventListener("click", (e) => this.selectProjectType(e));
    });

    // Form validation
    document
      .getElementById("projectName")
      ?.addEventListener("input", this.validateStep1);
    document
      .getElementById("startDate")
      ?.addEventListener("change", this.validateStep1);

    // Financial inputs with real-time validation
    document
      .getElementById("monthlyPrice")
      ?.addEventListener("input", this.updateFinancialPreview);
    document
      .getElementById("totalAmount")
      ?.addEventListener("input", this.updateFinancialPreview);
    document
      .getElementById("paidAmount")
      ?.addEventListener("input", this.updateFinancialPreview);

    // Modal events
    const modal = document.getElementById("addProjectModal");
    modal?.addEventListener("hidden.bs.modal", () => this.resetForm());
    modal?.addEventListener("shown.bs.modal", () => this.focusFirstInput());

    // Search and filters with debouncing
    document
      .getElementById("searchInput")
      ?.addEventListener(
        "input",
        this.debounce(this.filterProjects.bind(this), 300)
      );
    document
      .getElementById("typeFilter")
      ?.addEventListener("change", this.filterProjects.bind(this));
    document
      .getElementById("statusFilter")
      ?.addEventListener("change", this.filterProjects.bind(this));
  }

  async loadInitialData() {
    try {
      await Promise.all([this.loadProjects(), this.loadClients()]);
      this.updateStatistics();
      this.showWelcomeAnimation();
    } catch (error) {
      console.error("Error loading initial data:", error);
      this.showError("حدث خطأ في تحميل البيانات");
    }
  }

  async loadProjects() {
    try {
      // Use the public API endpoint that doesn't require authentication
      const response = await fetch("/api/v1/projects/api", {
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      this.projects = data.projects || [];
      this.filteredProjects = [...this.projects];
      this.displayProjects();
      return this.projects;
    } catch (error) {
      console.error("Error loading projects:", error);
      // Fallback: show demo data or empty state
      this.projects = [];
      this.filteredProjects = [];
      this.displayProjects();
      this.showError("لا يمكن تحميل المشاريع حالياً");
      return [];
    }
  }

  async loadClients() {
    try {
      const response = await fetch("/api/v1/clients/api", {
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      this.clients = data.clients || [];
      this.populateClientSelect();
      return this.clients;
    } catch (error) {
      console.error("Error loading clients:", error);
      this.clients = [];
      this.populateClientSelect();
      return [];
    }
  }

  populateClientSelect() {
    const select = document.getElementById("clientId");
    if (!select) return;

    select.innerHTML =
      '<option value="">اختر عميل موجود أو اتركه فارغاً</option>';

    this.clients.forEach((client) => {
      const option = document.createElement("option");
      option.value = client.id;
      option.textContent = client.name;
      select.appendChild(option);
    });
  }

  selectProjectType(event) {
    document.querySelectorAll(".type-option").forEach((opt) => {
      opt.classList.remove("selected");
    });

    event.currentTarget.classList.add("selected");

    const type = event.currentTarget.dataset.type;
    document.getElementById("projectType").value = type;

    this.updateFinancialSection(type);
    this.addTypeSelectionFeedback(event.currentTarget);
  }

  addTypeSelectionFeedback(element) {
    element.style.transform = "scale(0.95)";
    setTimeout(() => {
      element.style.transform = "scale(1)";
    }, 150);
  }

  updateFinancialSection(type) {
    const subscriptionDiv = document.getElementById("subscriptionFinancial");
    const onetimeDiv = document.getElementById("onetimeFinancial");

    if (!subscriptionDiv || !onetimeDiv) return;

    subscriptionDiv.style.opacity = "0";
    onetimeDiv.style.opacity = "0";

    setTimeout(() => {
      if (type === "subscription") {
        subscriptionDiv.style.display = "block";
        onetimeDiv.style.display = "none";
        setTimeout(() => (subscriptionDiv.style.opacity = "1"), 50);
      } else if (type === "onetime") {
        subscriptionDiv.style.display = "none";
        onetimeDiv.style.display = "block";
        setTimeout(() => (onetimeDiv.style.opacity = "1"), 50);
      }
    }, 200);
  }

  nextStep() {
    if (this.validateCurrentStep()) {
      if (this.currentStep < this.maxSteps) {
        this.currentStep++;
        this.updateStepDisplay();
        this.playStepTransition();
      }
    }
  }

  previousStep() {
    if (this.currentStep > 1) {
      this.currentStep--;
      this.updateStepDisplay();
      this.playStepTransition();
    }
  }

  updateStepDisplay() {
    document.querySelectorAll(".step-item").forEach((item, index) => {
      item.classList.remove("active", "completed");
      if (index + 1 < this.currentStep) {
        item.classList.add("completed");
      } else if (index + 1 === this.currentStep) {
        item.classList.add("active");
      }
    });

    document.querySelectorAll(".step-content").forEach((content, index) => {
      content.classList.remove("active");
      if (index + 1 === this.currentStep) {
        content.classList.add("active");
      }
    });

    const progress = ((this.currentStep - 1) / (this.maxSteps - 1)) * 100;
    const progressBar = document.getElementById("stepProgress");
    if (progressBar) {
      progressBar.style.width = progress + "%";
    }

    this.updateNavigationButtons();

    const currentStepEl = document.getElementById("currentStep");
    if (currentStepEl) {
      currentStepEl.textContent = this.currentStep;
    }

    if (this.currentStep === 3) {
      this.updateReviewContent();
    }
  }

  updateNavigationButtons() {
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");
    const saveBtn = document.getElementById("saveBtn");

    if (prevBtn)
      prevBtn.style.display = this.currentStep > 1 ? "inline-flex" : "none";
    if (nextBtn)
      nextBtn.style.display =
        this.currentStep < this.maxSteps ? "inline-flex" : "none";
    if (saveBtn)
      saveBtn.style.display =
        this.currentStep === this.maxSteps ? "inline-flex" : "none";
  }

  playStepTransition() {
    const activeContent = document.querySelector(".step-content.active");
    if (activeContent) {
      activeContent.style.opacity = "0";
      activeContent.style.transform = "translateX(20px)";

      setTimeout(() => {
        activeContent.style.opacity = "1";
        activeContent.style.transform = "translateX(0)";
      }, 50);
    }
  }

  validateCurrentStep() {
    switch (this.currentStep) {
      case 1:
        return this.validateStep1();
      case 2:
        return this.validateStep2();
      default:
        return true;
    }
  }

  validateStep1() {
    const projectName = document.getElementById("projectName")?.value.trim();
    const projectType = document.getElementById("projectType")?.value;
    const startDate = document.getElementById("startDate")?.value;

    const errors = [];

    if (!projectName) {
      errors.push("يرجى إدخال اسم المشروع");
    }

    if (!projectType) {
      errors.push("يرجى اختيار نوع المشروع");
    }

    if (!startDate) {
      errors.push("يرجى إدخال تاريخ البداية");
    }

    if (errors.length > 0) {
      this.showValidationErrors(errors);
      return false;
    }

    return true;
  }

  validateStep2() {
    const projectType = document.getElementById("projectType")?.value;
    const errors = [];

    if (projectType === "subscription") {
      const monthlyPrice = document.getElementById("monthlyPrice")?.value;
      if (!monthlyPrice || parseFloat(monthlyPrice) <= 0) {
        errors.push("يرجى إدخال قيمة صحيحة للاشتراك الشهري");
      }
    } else if (projectType === "onetime") {
      const totalAmount = document.getElementById("totalAmount")?.value;
      if (!totalAmount || parseFloat(totalAmount) <= 0) {
        errors.push("يرجى إدخال قيمة صحيحة للمبلغ الإجمالي");
      }

      const paidAmount = document.getElementById("paidAmount")?.value;
      if (paidAmount && parseFloat(paidAmount) > parseFloat(totalAmount)) {
        errors.push("المبلغ المدفوع لا يمكن أن يكون أكبر من المبلغ الإجمالي");
      }
    }

    if (errors.length > 0) {
      this.showValidationErrors(errors);
      return false;
    }

    return true;
  }

  showValidationErrors(errors) {
    this.showError(errors.join("\n"));
  }

  updateReviewContent() {
    const reviewContent = document.getElementById("reviewContent");
    if (!reviewContent) return;

    const formData = this.collectFormData();

    let financialInfo = "";
    if (formData.type === "subscription") {
      financialInfo = `
                <div class="alert alert-info">
                    <i class="fas fa-sync-alt me-2"></i>
                    <strong>اشتراك شهري:</strong> ${formData.monthly_price} ج.م شهرياً
                </div>
            `;
    } else {
      const remaining =
        (formData.total_amount || 0) - (formData.paid_amount || 0);
      financialInfo = `
                <div class="row">
                    <div class="col-md-4">
                        <div class="alert alert-primary">
                            <strong>المبلغ الإجمالي:</strong><br>${
                              formData.total_amount
                            } ج.م
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="alert alert-success">
                            <strong>المبلغ المدفوع:</strong><br>${
                              formData.paid_amount || 0
                            } ج.م
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="alert alert-warning">
                            <strong>المبلغ المتبقي:</strong><br>${remaining} ج.م
                        </div>
                    </div>
                </div>
            `;
    }

    const clientInfo = formData.client_id
      ? this.clients.find((c) => c.id == formData.client_id)?.name ||
        "عميل غير معروف"
      : "لا يوجد عميل محدد";

    reviewContent.innerHTML = `
            <div class="card border-0 shadow-sm">
                <div class="card-header bg-light">
                    <h5 class="mb-0">
                        <i class="fas fa-project-diagram me-2 text-primary"></i>
                        ${formData.name}
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <strong>نوع المشروع:</strong>
                            <span class="badge bg-${
                              formData.type === "subscription"
                                ? "primary"
                                : "success"
                            } ms-2">
                                ${
                                  formData.type === "subscription"
                                    ? "اشتراك شهري"
                                    : "دفع كامل"
                                }
                            </span>
                        </div>
                        <div class="col-md-6">
                            <strong>العميل:</strong> ${clientInfo}
                        </div>
                    </div>
                    
                    ${
                      formData.description
                        ? `
                        <div class="mb-3">
                            <strong>الوصف:</strong>
                            <p class="text-muted mt-1">${formData.description}</p>
                        </div>
                    `
                        : ""
                    }
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <strong>تاريخ البداية:</strong> ${this.formatDate(
                              formData.start_date
                            )}
                        </div>
                        ${
                          formData.end_date
                            ? `
                            <div class="col-md-6">
                                <strong>تاريخ الانتهاء:</strong> ${this.formatDate(
                                  formData.end_date
                                )}
                            </div>
                        `
                            : ""
                        }
                    </div>
                    
                    <div class="mb-3">
                        <strong>التفاصيل المالية:</strong>
                        ${financialInfo}
                    </div>
                </div>
            </div>
        `;
  }

  collectFormData() {
    return {
      name: document.getElementById("projectName")?.value || "",
      project_type: document.getElementById("projectType")?.value || "",
      description: document.getElementById("description")?.value || "",
      start_date: document.getElementById("startDate")?.value || "",
      end_date: document.getElementById("endDate")?.value || "",
      client_id: document.getElementById("clientId")?.value || null,
      monthly_price: document.getElementById("monthlyPrice")?.value || 0,
      total_amount: document.getElementById("totalAmount")?.value || 0,
      paid_amount: document.getElementById("paidAmount")?.value || 0,
    };
  }

  async saveProject() {
    const formData = this.collectFormData();

    this.showLoading(true);

    try {
      const response = await fetch("/api/v1/projects/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (data.success) {
        this.showSuccess("تم إنشاء المشروع بنجاح!");
        this.closeModal();
        await this.loadProjects();
        this.updateStatistics();
      } else {
        this.showError("حدث خطأ: " + (data.message || "خطأ غير معروف"));
      }
    } catch (error) {
      console.error("Error saving project:", error);
      this.showError("حدث خطأ في الاتصال بالخادم");
    } finally {
      this.showLoading(false);
    }
  }

  displayProjects() {
    const grid = document.getElementById("projectsGrid");
    if (!grid) return;

    if (this.filteredProjects.length === 0) {
      grid.innerHTML = this.getEmptyState();
      return;
    }

    grid.innerHTML = this.filteredProjects
      .map((project) => this.createProjectCard(project))
      .join("");
    this.animateProjectCards();
  }

  createProjectCard(project) {
    const statusColors = {
      active: "success",
      completed: "primary",
      "on-hold": "warning",
      cancelled: "danger",
    };

    const statusLabels = {
      active: "نشط",
      completed: "مكتمل",
      "on-hold": "معلق",
      cancelled: "ملغي",
    };

    // Create action buttons based on project type
    let actionButtons = `
        <button class="btn btn-outline-info btn-sm" onclick="projectManager.viewProject(${project.id})">
            <i class="fas fa-eye"></i>
            عرض
        </button>
        <button class="btn btn-outline-primary btn-sm" onclick="projectManager.editProject(${project.id})">
            <i class="fas fa-edit"></i>
            تعديل
        </button>
    `;

    // Add subscribers button for subscription projects
    if (project.project_type === "subscription") {
      actionButtons += `
            <button class="btn btn-outline-success btn-sm" onclick="projectManager.viewSubscribers(${project.id})">
                <i class="fas fa-users"></i>
                المشتركين
            </button>
        `;
    }

    actionButtons += `
        <button class="btn btn-outline-danger btn-sm" onclick="projectManager.deleteProject(${project.id})">
            <i class="fas fa-trash"></i>
            حذف
        </button>
    `;

    return `
            <div class="col-lg-6 col-xl-4 mb-4 project-card-container" data-project-id="${
              project.id
            }">
                <div class="project-card h-100">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <h5 class="card-title mb-0">${project.name}</h5>
                        <div class="d-flex flex-column align-items-end gap-1">
                            <span class="badge bg-${
                              project.project_type === "subscription"
                                ? "primary"
                                : "info"
                            }">
                                ${
                                  project.project_type === "subscription"
                                    ? "اشتراك شهري"
                                    : "دفع كامل"
                                }
                            </span>
                            <span class="badge bg-${
                              statusColors[project.status] || "secondary"
                            }">
                                ${
                                  statusLabels[project.status] || project.status
                                }
                            </span>
                        </div>
                    </div>
                    
                    ${
                      project.description
                        ? `
                        <p class="text-muted small mb-3">${project.description}</p>
                    `
                        : ""
                    }
                    
                    <div class="mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <small class="text-muted">
                                <i class="fas fa-calendar-alt me-1"></i>
                                ${this.formatDate(project.start_date)}
                            </small>
                            ${
                              project.client_name
                                ? `
                                <small class="text-muted">
                                    <i class="fas fa-user me-1"></i>
                                    ${project.client_name}
                                </small>
                            `
                                : ""
                            }
                        </div>
                    </div>
                    
                    <div class="mt-auto">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div class="text-primary fw-bold">
                                ${
                                  project.project_type === "subscription"
                                    ? `${this.formatCurrency(
                                        project.monthly_price
                                      )}/شهرياً`
                                    : this.formatCurrency(project.total_amount)
                                }
                            </div>
                            ${
                              project.project_type === "onetime" &&
                              project.paid_amount
                                ? `
                                <small class="text-success">
                                    مدفوع: ${this.formatCurrency(
                                      project.paid_amount
                                    )}
                                </small>
                            `
                                : ""
                            }
                        </div>
                        
                        <div class="btn-group-vertical w-100 gap-1">
                            ${actionButtons}
                        </div>
                    </div>
                </div>
            </div>
        `;
  }

  getEmptyState() {
    return `
            <div class="col-12 text-center py-5">
                <div class="empty-state">
                    <i class="fas fa-folder-open fa-4x text-muted mb-4"></i>
                    <h4 class="text-muted mb-3">لا توجد مشاريع حالياً</h4>
                    <p class="text-muted mb-4">ابدأ رحلتك بإنشاء مشروعك الأول</p>
                    <button class="btn btn-primary btn-lg" data-bs-toggle="modal" data-bs-target="#addProjectModal">
                        <i class="fas fa-plus me-2"></i>
                        إضافة مشروع جديد
                    </button>
                </div>
            </div>
        `;
  }

  updateStatistics() {
    const subscriptionCount = this.projects.filter(
      (p) => p.project_type === "subscription"
    ).length;
    const onetimeCount = this.projects.filter(
      (p) => p.project_type === "onetime"
    ).length;
    const completedCount = this.projects.filter(
      (p) => p.status === "completed"
    ).length;
    const monthlyRevenue = this.projects
      .filter((p) => p.project_type === "subscription" && p.status === "active")
      .reduce((sum, p) => sum + (parseFloat(p.monthly_price) || 0), 0);

    document.getElementById("subscriptionCount").textContent =
      subscriptionCount;
    document.getElementById("onetimeCount").textContent = onetimeCount;
    document.getElementById("completedCount").textContent = completedCount;
    document.getElementById("monthlyRevenue").textContent =
      monthlyRevenue.toLocaleString();
  }

  initializeAnimations() {
    // Basic animations setup
  }

  animateProjectCards() {
    // Basic card animations
  }

  showWelcomeAnimation() {
    // Welcome animation
  }

  focusFirstInput() {
    setTimeout(() => {
      const firstInput = document.getElementById("projectName");
      if (firstInput) {
        firstInput.focus();
      }
    }, 300);
  }

  async viewProject(id) {
    try {
      this.showLoading(true);

      const project = this.projects.find((p) => p.id === id);
      if (!project) {
        this.showError("المشروع غير موجود");
        return;
      }

      // Populate project details modal
      const detailsContent = this.generateProjectDetailsHTML(project);
      document.getElementById("projectDetailsContent").innerHTML =
        detailsContent;

      // Store current project ID for edit button
      document.getElementById("editProjectBtn").onclick = () =>
        this.editProject(id);

      // Show the modal
      const modal = new bootstrap.Modal(
        document.getElementById("projectDetailsModal")
      );
      modal.show();
    } catch (error) {
      console.error("Error viewing project:", error);
      this.showError("حدث خطأ في عرض تفاصيل المشروع");
    } finally {
      this.showLoading(false);
    }
  }

  generateProjectDetailsHTML(project) {
    const statusBadges = {
      active: '<span class="badge bg-success">🟢 نشط</span>',
      completed: '<span class="badge bg-primary">✅ مكتمل</span>',
      "on-hold": '<span class="badge bg-warning">⏸️ معلق</span>',
      cancelled: '<span class="badge bg-danger">❌ ملغي</span>',
    };

    const typeBadge =
      project.project_type === "subscription"
        ? '<span class="badge bg-primary">🔄 اشتراك شهري</span>'
        : '<span class="badge bg-info">💰 دفع كامل</span>';

    let financialInfo = "";
    if (project.project_type === "subscription") {
      financialInfo = `
        <div class="alert alert-info">
          <h6><i class="fas fa-credit-card me-2"></i>تفاصيل الاشتراك</h6>
          <p><strong>قيمة الاشتراك الشهري:</strong> ${this.formatCurrency(
            project.monthly_price
          )}</p>
          <p><strong>الإيراد الشهري المتوقع:</strong> ${this.formatCurrency(
            project.monthly_price * (project.subscriber_count || 0)
          )}</p>
        </div>
      `;
    } else {
      const remaining =
        (project.total_amount || 0) - (project.paid_amount || 0);
      financialInfo = `
        <div class="row">
          <div class="col-md-4">
            <div class="alert alert-primary">
              <strong>المبلغ الإجمالي:</strong><br>${this.formatCurrency(
                project.total_amount
              )}
            </div>
          </div>
          <div class="col-md-4">
            <div class="alert alert-success">
              <strong>المبلغ المدفوع:</strong><br>${this.formatCurrency(
                project.paid_amount || 0
              )}
            </div>
          </div>
          <div class="col-md-4">
            <div class="alert alert-warning">
              <strong>المبلغ المتبقي:</strong><br>${this.formatCurrency(
                remaining
              )}
            </div>
          </div>
        </div>
      `;
    }

    return `
      <div class="project-details">
        <div class="row mb-4">
          <div class="col-md-8">
            <h4>${project.name}</h4>
            <p class="text-muted">${project.description || "لا يوجد وصف"}</p>
          </div>
          <div class="col-md-4 text-end">
            ${typeBadge}
            ${statusBadges[project.status] || project.status}
          </div>
        </div>

        <div class="row mb-3">
          <div class="col-md-6">
            <strong>📅 تاريخ البداية:</strong> ${this.formatDate(
              project.start_date
            )}
          </div>
          <div class="col-md-6">
            <strong>📅 تاريخ الانتهاء:</strong> ${
              this.formatDate(project.end_date) || "غير محدد"
            }
          </div>
        </div>

        ${
          project.client_name
            ? `
          <div class="mb-3">
            <strong>👤 العميل:</strong> ${project.client_name}
          </div>
        `
            : ""
        }

        <div class="mb-3">
          <strong>💰 التفاصيل المالية:</strong>
          ${financialInfo}
        </div>

        <div class="mb-3">
          <strong>📊 معلومات إضافية:</strong>
          <ul class="list-unstyled mt-2">
            <li><strong>تاريخ الإنشاء:</strong> ${this.formatDate(
              project.created_at
            )}</li>
            <li><strong>رمز المشروع:</strong> ${
              project.project_code || "غير محدد"
            }</li>
          </ul>
        </div>
      </div>
    `;
  }

  async editProject(id) {
    try {
      this.showLoading(true);

      const project = this.projects.find((p) => p.id === id);
      if (!project) {
        this.showError("المشروع غير موجود");
        return;
      }

      // Populate edit form
      document.getElementById("editProjectId").value = project.id;
      document.getElementById("editProjectName").value = project.name || "";
      document.getElementById("editProjectStatus").value =
        project.status || "active";
      document.getElementById("editDescription").value =
        project.description || "";
      document.getElementById("editStartDate").value = project.start_date
        ? project.start_date.split("T")[0]
        : "";
      document.getElementById("editEndDate").value = project.end_date
        ? project.end_date.split("T")[0]
        : "";

      // Add financial fields based on project type
      const financialSection = document.getElementById("editFinancialSection");
      if (project.project_type === "subscription") {
        financialSection.innerHTML = `
          <div class="mb-3">
            <label class="form-label">💳 قيمة الاشتراك الشهري (ج.م)</label>
            <input type="number" class="form-control" id="editMonthlyPrice" step="0.01" value="${
              project.monthly_price || ""
            }">
          </div>
        `;
      } else {
        financialSection.innerHTML = `
          <div class="row">
            <div class="col-md-6">
              <div class="mb-3">
                <label class="form-label">💰 إجمالي المبلغ (ج.م)</label>
                <input type="number" class="form-control" id="editTotalAmount" step="0.01" value="${
                  project.total_amount || ""
                }">
              </div>
            </div>
            <div class="col-md-6">
              <div class="mb-3">
                <label class="form-label">💸 المبلغ المدفوع (ج.م)</label>
                <input type="number" class="form-control" id="editPaidAmount" step="0.01" value="${
                  project.paid_amount || ""
                }">
              </div>
            </div>
          </div>
        `;
      }

      // Hide details modal and show edit modal
      const detailsModal = bootstrap.Modal.getInstance(
        document.getElementById("projectDetailsModal")
      );
      if (detailsModal) detailsModal.hide();

      const editModal = new bootstrap.Modal(
        document.getElementById("editProjectModal")
      );
      editModal.show();
    } catch (error) {
      console.error("Error editing project:", error);
      this.showError("حدث خطأ في تحضير نموذج التعديل");
    } finally {
      this.showLoading(false);
    }
  }

  async viewSubscribers(id) {
    try {
      this.showLoading(true);

      const project = this.projects.find((p) => p.id === id);
      if (!project) {
        this.showError("المشروع غير موجود");
        return;
      }

      if (project.project_type !== "subscription") {
        this.showError("هذا المشروع ليس من نوع الاشتراك الشهري");
        return;
      }

      // Load subscribers data
      await this.loadProjectSubscribers(id);

      // Show subscribers modal
      const modal = new bootstrap.Modal(
        document.getElementById("subscribersModal")
      );
      modal.show();
    } catch (error) {
      console.error("Error viewing subscribers:", error);
      this.showError("حدث خطأ في عرض المشتركين");
    } finally {
      this.showLoading(false);
    }
  }

  async loadProjectSubscribers(projectId) {
    try {
      // Use public API endpoint that doesn't require authentication
      const response = await fetch(
        `/api/v1/projects/${projectId}/subscribers/api`
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const subscribersContent = document.getElementById("subscribersContent");

      if (data.success && data.subscribers && data.subscribers.length > 0) {
        subscribersContent.innerHTML = `
          <div class="table-responsive">
            <table class="table table-striped">
              <thead>
                <tr>
                  <th>👤 اسم العميل</th>
                  <th>📧 البريد الإلكتروني</th>
                  <th>📞 الهاتف</th>
                  <th>📅 تاريخ الاشتراك</th>
                  <th>⚙️ الإجراءات</th>
                </tr>
              </thead>
              <tbody>
                ${data.subscribers
                  .map((subscriber) => {
                    // Debug log to check data structure
                    console.log("Subscriber data:", subscriber);

                    // Make sure client_id exists
                    const clientId = subscriber.client_id || subscriber.id;
                    if (!clientId) {
                      console.error(
                        "Missing client_id for subscriber:",
                        subscriber
                      );
                      return "";
                    }

                    return `
                    <tr>
                      <td>${
                        subscriber.client_name || subscriber.name || "غير محدد"
                      }</td>
                      <td>${
                        subscriber.client_email || subscriber.email || "-"
                      }</td>
                      <td>${
                        subscriber.client_phone || subscriber.phone || "-"
                      }</td>
                      <td>${this.formatDate(subscriber.subscription_date)}</td>
                      <td>
                        <button class="btn btn-danger btn-sm" 
                                onclick="projectManager.removeSubscriber(${projectId}, ${clientId})"
                                title="إزالة المشترك">
                          🗑️ إزالة
                        </button>
                      </td>
                    </tr>
                  `;
                  })
                  .join("")}
              </tbody>
            </table>
          </div>
        `;
      } else {
        subscribersContent.innerHTML = `
          <div class="text-center py-4">
            <p class="text-muted">📭 لا يوجد مشتركين في هذا المشروع حالياً</p>
            <button class="btn btn-primary" onclick="projectManager.addSubscriber(${projectId})">
              ➕ إضافة أول مشترك
            </button>
          </div>
        `;
      }

      // Set project ID for add subscriber function
      document.getElementById("subscriberProjectId").value = projectId;
    } catch (error) {
      console.error("Error loading subscribers:", error);
      document.getElementById("subscribersContent").innerHTML = `
        <div class="alert alert-danger">
          ❌ حدث خطأ في تحميل قائمة المشتركين
          <br><small>التفاصيل: ${error.message}</small>
        </div>
      `;
    }
  }

  async deleteProject(id) {
    const project = this.projects.find((p) => p.id === id);
    if (!project) return;

    if (
      confirm(
        `هل أنت متأكد من حذف المشروع "${project.name}"؟\nهذا الإجراء لا يمكن التراجع عنه.`
      )
    ) {
      this.showLoading(true);

      try {
        // Use public API endpoint that doesn't require authentication
        const response = await fetch(`/api/v1/projects/${id}/api`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();

        if (data.success) {
          this.showSuccess("تم حذف المشروع بنجاح");
          await this.loadProjects();
          this.updateStatistics();
        } else {
          this.showError(data.message || "حدث خطأ في حذف المشروع");
        }
      } catch (error) {
        console.error("Error deleting project:", error);
        this.showError(`حدث خطأ في الاتصال بالخادم: ${error.message}`);
      } finally {
        this.showLoading(false);
      }
    }
  }

  formatDate(dateString) {
    if (!dateString) return "غير محدد";
    const date = new Date(dateString);
    return date.toLocaleDateString("ar-EG");
  }

  formatCurrency(amount, includeSymbol = true) {
    const formatted = parseFloat(amount || 0).toLocaleString("ar-EG", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
    return includeSymbol ? `${formatted} ج.م` : formatted;
  }

  debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  showLoading(show) {
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) {
      if (show) {
        overlay.style.display = "flex";
        overlay.classList.add("show");
        // Auto-hide after 30 seconds to prevent stuck loading
        this.loadingTimeout = setTimeout(() => {
          this.forceHideLoading();
        }, 30000);
      } else {
        overlay.style.display = "none";
        overlay.classList.remove("show");
        // Clear timeout
        if (this.loadingTimeout) {
          clearTimeout(this.loadingTimeout);
          this.loadingTimeout = null;
        }
      }
    }
  }

  // Force hide loading overlay
  forceHideLoading() {
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) {
      overlay.style.display = "none";
      overlay.classList.remove("show");
    }

    if (this.loadingTimeout) {
      clearTimeout(this.loadingTimeout);
      this.loadingTimeout = null;
    }

    console.warn("Loading overlay was forcefully hidden after timeout");
  }

  showSuccess(message) {
    // Hide loading first
    this.showLoading(false);
    this.showToast(message, "success");
  }

  showError(message) {
    // Hide loading first
    this.showLoading(false);
    this.showToast(message, "error");
  }

  showToast(message, type = "info") {
    // Ensure loading is hidden before showing toast
    this.forceHideLoading();

    // Simple alert for now - can be enhanced with toast library
    alert(message);
  }

  resetForm() {
    this.currentStep = 1;
    document.getElementById("addProjectForm")?.reset();
    document.getElementById("projectType").value = "";
    document
      .querySelectorAll(".type-option")
      .forEach((opt) => opt.classList.remove("selected"));
    this.updateStepDisplay();
  }

  closeModal() {
    const modal = bootstrap.Modal.getInstance(
      document.getElementById("addProjectModal")
    );
    if (modal) {
      modal.hide();
    }
  }

  filterProjects() {
    const searchTerm =
      document.getElementById("searchInput")?.value.toLowerCase() || "";
    const typeFilter = document.getElementById("typeFilter")?.value || "";
    const statusFilter = document.getElementById("statusFilter")?.value || "";

    this.filteredProjects = this.projects.filter((project) => {
      const matchesSearch =
        !searchTerm ||
        project.name.toLowerCase().includes(searchTerm) ||
        (project.description &&
          project.description.toLowerCase().includes(searchTerm)) ||
        (project.client_name &&
          project.client_name.toLowerCase().includes(searchTerm));

      const matchesType = !typeFilter || project.project_type === typeFilter;
      const matchesStatus = !statusFilter || project.status === statusFilter;

      return matchesSearch && matchesType && matchesStatus;
    });

    this.displayProjects();
  }

  async updateProject() {
    try {
      this.showLoading(true);

      const projectId = document.getElementById("editProjectId").value;
      const formData = {
        name: document.getElementById("editProjectName").value,
        status: document.getElementById("editProjectStatus").value,
        description: document.getElementById("editDescription").value,
        start_date: document.getElementById("editStartDate").value,
        end_date: document.getElementById("editEndDate").value,
      };

      // Add financial data based on project type
      const project = this.projects.find((p) => p.id == projectId);
      if (project.project_type === "subscription") {
        formData.monthly_price =
          document.getElementById("editMonthlyPrice").value;
      } else {
        formData.total_amount =
          document.getElementById("editTotalAmount").value;
        formData.paid_amount = document.getElementById("editPaidAmount").value;
      }

      // Use public API endpoint that doesn't require authentication
      const response = await fetch(`/api/v1/projects/${projectId}/api`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();

      if (data.success) {
        this.showSuccess("تم تحديث المشروع بنجاح");

        // Hide edit modal
        const editModal = bootstrap.Modal.getInstance(
          document.getElementById("editProjectModal")
        );
        if (editModal) editModal.hide();

        // Reload projects
        await this.loadProjects();
        this.updateStatistics();
      } else {
        this.showError(data.message || "حدث خطأ في تحديث المشروع");
      }
    } catch (error) {
      console.error("Error updating project:", error);
      this.showError(`حدث خطأ في الاتصال بالخادم: ${error.message}`);
    } finally {
      this.showLoading(false);
    }
  }

  async addSubscriber(projectId) {
    try {
      this.showLoading(true);

      // Set project ID
      document.getElementById("subscriberProjectId").value = projectId;

      // Populate client dropdown
      await this.populateSubscriberClientSelect();

      // Set default date to today
      const today = new Date().toISOString().split("T")[0];
      document.getElementById("subscriptionStartDate").value = today;

      // Hide subscribers modal and show add subscriber modal
      const subscribersModal = bootstrap.Modal.getInstance(
        document.getElementById("subscribersModal")
      );
      if (subscribersModal) subscribersModal.hide();

      const addModal = new bootstrap.Modal(
        document.getElementById("addSubscriberModal")
      );
      addModal.show();
    } catch (error) {
      console.error("Error preparing add subscriber:", error);
      this.showError("حدث خطأ في تحضير نموذج إضافة المشترك");
    } finally {
      this.showLoading(false);
    }
  }

  async populateSubscriberClientSelect() {
    try {
      const response = await fetch("/api/v1/clients/api");
      const data = await response.json();

      const select = document.getElementById("subscriberClientId");
      select.innerHTML = '<option value="">اختر عميل...</option>';

      if (data.success && data.clients) {
        data.clients.forEach((client) => {
          const option = document.createElement("option");
          option.value = client.id;
          option.textContent = client.name;
          select.appendChild(option);
        });
      }
    } catch (error) {
      console.error("Error loading clients for subscriber:", error);
      this.showError("حدث خطأ في تحميل قائمة العملاء");
    }
  }

  async saveSubscriber() {
    try {
      this.showLoading(true);

      const projectId = document.getElementById("subscriberProjectId").value;
      const clientId = document.getElementById("subscriberClientId").value;
      const startDate = document.getElementById("subscriptionStartDate").value;

      if (!clientId) {
        this.showError("يرجى اختيار عميل");
        return;
      }

      // Use public API endpoint that doesn't require authentication
      const response = await fetch(
        `/api/v1/projects/${projectId}/subscribers/api`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            client_id: clientId,
            subscription_date: startDate,
          }),
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();

      if (data.success) {
        this.showSuccess("تم إضافة المشترك بنجاح");

        // Hide add subscriber modal
        const addModal = bootstrap.Modal.getInstance(
          document.getElementById("addSubscriberModal")
        );
        if (addModal) addModal.hide();

        // Reload subscribers
        await this.loadProjectSubscribers(projectId);

        // Show subscribers modal again
        const subscribersModal = new bootstrap.Modal(
          document.getElementById("subscribersModal")
        );
        subscribersModal.show();
      } else {
        this.showError(data.message || "حدث خطأ في إضافة المشترك");
      }
    } catch (error) {
      console.error("Error saving subscriber:", error);
      this.showError(`حدث خطأ في الاتصال بالخادم: ${error.message}`);
    } finally {
      this.showLoading(false);
    }
  }

  async removeSubscriber(projectId, clientId) {
    // Validate inputs
    if (!projectId || !clientId) {
      this.showError("معرف المشروع أو العميل غير صحيح");
      console.error("Invalid IDs:", { projectId, clientId });
      return;
    }

    if (!confirm("هل أنت متأكد من إزالة هذا المشترك؟")) {
      return;
    }

    try {
      this.showLoading(true);

      console.log(
        `Removing subscriber: projectId=${projectId}, clientId=${clientId}`
      );

      // Use public API endpoint that doesn't require authentication
      const response = await fetch(
        `/api/v1/projects/${projectId}/subscribers/${clientId}/api`,
        {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();

      if (data.success) {
        this.showSuccess("تم إزالة المشترك بنجاح");
        await this.loadProjectSubscribers(projectId);
      } else {
        this.showError(data.message || "حدث خطأ في إزالة المشترك");
      }
    } catch (error) {
      console.error("Error removing subscriber:", error);
      this.showError(`حدث خطأ في الاتصال بالخادم: ${error.message}`);
    } finally {
      this.showLoading(false);
    }
  }
}

// Global instance
let projectManager;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  projectManager = new ProjectManager();
});

// Global error handlers to prevent stuck loading
window.addEventListener("error", function (event) {
  console.error("Global JavaScript error:", event.error);
  if (projectManager) {
    projectManager.forceHideLoading();
  }
});

window.addEventListener("unhandledrejection", function (event) {
  console.error("Unhandled promise rejection:", event.reason);
  if (projectManager) {
    projectManager.forceHideLoading();
  }
});

// Global click handler to hide loading on any critical interaction
document.addEventListener("click", function (e) {
  // If user clicks on modal backdrop or close buttons, ensure loading is hidden
  if (
    e.target.classList.contains("modal-backdrop") ||
    e.target.classList.contains("btn-close") ||
    e.target.closest(".btn-close")
  ) {
    if (projectManager) {
      projectManager.forceHideLoading();
    }
  }
});

// Global functions for template compatibility
function nextStep() {
  projectManager?.nextStep();
}

function previousStep() {
  projectManager?.previousStep();
}

function saveProject() {
  projectManager?.saveProject();
}

function filterProjects() {
  projectManager?.filterProjects();
}

function updateProject() {
  projectManager?.updateProject();
}

function addSubscriber() {
  const projectId = document.getElementById("subscriberProjectId").value;
  projectManager?.addSubscriber(projectId);
}

function saveSubscriber() {
  projectManager?.saveSubscriber();
}

// Emergency function to force hide loading (can be called from browser console)
function forceHideLoading() {
  if (projectManager) {
    projectManager.forceHideLoading();
  } else {
    // Fallback if projectManager not available
    const overlay = document.getElementById("loadingOverlay");
    if (overlay) {
      overlay.style.display = "none";
      overlay.classList.remove("show");
    }
  }
  console.log("Loading overlay forcefully hidden");
}
