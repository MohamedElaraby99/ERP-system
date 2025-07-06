// Dashboard JavaScript - Optimized for Offline-First

// Cache configuration
let cachedData = {};
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Initialize dashboard
document.addEventListener("DOMContentLoaded", function () {
  // Check authentication
  const token = localStorage.getItem("access_token");
  if (!token) {
    window.location.href = "/login";
    return;
  }

  // Set user name
  const user = JSON.parse(localStorage.getItem("user") || "{}");
  document.getElementById("userName").textContent = user.email || "المستخدم";

  // Load dashboard data
  loadDashboardData();
  initializeCharts();

  // Setup logout handler
  document.querySelector(".btn-logout").addEventListener("click", logout);
});

// Optimized data loading with caching
async function loadDashboardData() {
  const token = localStorage.getItem("access_token");
  if (!token) {
    window.location.href = "/login";
    return;
  }

  const now = Date.now();
  if (cachedData.timestamp && now - cachedData.timestamp < CACHE_DURATION) {
    updateCountsFromCache();
    return;
  }

  try {
    showLoadingState();

    // Load data in parallel for better performance using correct API endpoints
    const [projectsRes, employeesRes, tasksRes, clientsRes] = await Promise.all(
      [
        fetch("/api/v1/projects/", {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch("/api/v1/employees/", {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch("/api/v1/tasks/", {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch("/api/v1/clients/", {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]
    );

    // Check for unauthorized access
    if (
      projectsRes.status === 401 ||
      employeesRes.status === 401 ||
      tasksRes.status === 401 ||
      clientsRes.status === 401
    ) {
      // Token expired or invalid, try to refresh
      const refreshed = await refreshToken();
      if (refreshed) {
        // Retry loading data
        loadDashboardData();
        return;
      } else {
        // Redirect to login if refresh failed
        window.location.href = "/login";
        return;
      }
    }

    // Process responses with better error handling
    const results = await Promise.all([
      projectsRes.ok ? projectsRes.json().catch(() => []) : [],
      employeesRes.ok ? employeesRes.json().catch(() => []) : [],
      tasksRes.ok ? tasksRes.json().catch(() => []) : [],
      clientsRes.ok ? clientsRes.json().catch(() => []) : [],
    ]);

    const [projects, employees, tasks, clients] = results;

    // Ensure arrays and handle different response formats
    const projectsArray = Array.isArray(projects)
      ? projects
      : projects?.projects || [];
    const employeesArray = Array.isArray(employees)
      ? employees
      : employees?.employees || [];
    const tasksArray = Array.isArray(tasks) ? tasks : tasks?.tasks || [];
    const clientsArray = Array.isArray(clients)
      ? clients
      : clients?.clients || [];

    // Cache data
    cachedData = {
      projects: projectsArray.length,
      employees: employeesArray.length,
      tasks: tasksArray.filter((task) => task && task.status !== "completed")
        .length,
      clients: clientsArray.length,
      timestamp: now,
    };

    updateCountsFromCache();
  } catch (error) {
    console.error("Error loading dashboard data:", error);
    hideLoadingState();
    // Show fallback counts
    cachedData = {
      projects: 0,
      employees: 0,
      tasks: 0,
      clients: 0,
      timestamp: now,
    };
    updateCountsFromCache();
  }
}

// Token refresh function
async function refreshToken() {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return false;

  try {
    const response = await fetch("/auth/refresh", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${refreshToken}`,
      },
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem("access_token", data.access_token);
      return true;
    }
  } catch (error) {
    console.error("Error refreshing token:", error);
  }

  // Clear tokens if refresh failed
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  return false;
}

function updateCountsFromCache() {
  updateCount("projectsCount", cachedData.projects || 0);
  updateCount("employeesCount", cachedData.employees || 0);
  updateCount("tasksCount", cachedData.tasks || 0);
  updateCount("clientsCount", cachedData.clients || 0);
}

function showLoadingState() {
  ["projectsCount", "employeesCount", "tasksCount", "clientsCount"].forEach(
    (id) => {
      const element = document.getElementById(id);
      if (element) {
        element.textContent = "...";
        element.classList.add("loading-skeleton");
      }
    }
  );
}

function hideLoadingState() {
  ["projectsCount", "employeesCount", "tasksCount", "clientsCount"].forEach(
    (id) => {
      const element = document.getElementById(id);
      if (element) {
        element.classList.remove("loading-skeleton");
      }
    }
  );
}

function updateCount(elementId, value) {
  const element = document.getElementById(elementId);
  if (!element) return;

  element.classList.remove("loading-skeleton");

  // Optimized counter animation
  let current = 0;
  const increment = Math.max(1, Math.floor(value / 10));
  const timer = setInterval(() => {
    current += increment;
    if (current >= value) {
      current = value;
      clearInterval(timer);
    }
    element.textContent = current;
  }, 30);
}

// Initialize charts
function initializeCharts() {
  // Revenue Chart
  const revenueCtx = document.getElementById("revenueChart").getContext("2d");
  new Chart(revenueCtx, {
    type: "line",
    data: {
      labels: ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو"],
      datasets: [
        {
          label: "الإيرادات الشهرية",
          data: [0, 0, 0, 0, 0, 0],
          borderColor: "#4f46e5",
          tension: 0.4,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
        },
      },
    },
  });

  // Projects Chart
  const projectsCtx = document.getElementById("projectsChart").getContext("2d");
  new Chart(projectsCtx, {
    type: "doughnut",
    data: {
      labels: ["نشط", "مكتمل", "متوقف"],
      datasets: [
        {
          data: [0, 0, 0],
          backgroundColor: ["#4f46e5", "#10b981", "#f59e0b"],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
        },
      },
    },
  });
}

// Update counts
function updateCounts(counts) {
  document.getElementById("projectsCount").textContent = counts.projects || 0;
  document.getElementById("clientsCount").textContent = counts.clients || 0;
  document.getElementById("employeesCount").textContent = counts.employees || 0;
  document.getElementById("tasksCount").textContent = counts.tasks || 0;
}

// Update activities
function updateActivities(activities) {
  const activitiesList = document.getElementById("activitiesList");
  activitiesList.innerHTML = "";

  activities.forEach((activity) => {
    const activityItem = document.createElement("div");
    activityItem.className = "activity-item";
    activityItem.innerHTML = `
      <div class="activity-icon">
        <span class="material-icons">${getActivityIcon(activity.type)}</span>
      </div>
      <div class="activity-content">
        <div class="activity-title">${activity.title}</div>
        <div class="activity-description">${activity.description}</div>
        <div class="activity-time">${formatDate(activity.timestamp)}</div>
      </div>
    `;
    activitiesList.appendChild(activityItem);
  });
}

// Get activity icon based on type
function getActivityIcon(type) {
  const icons = {
    project_created: "work",
    subscription_created: "sync_alt",
    payment_received: "payments",
    task_completed: "task_alt",
    client_added: "person_add",
    employee_added: "group_add",
  };
  return icons[type] || "info";
}

// Format date
function formatDate(timestamp) {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  // Less than 24 hours
  if (diff < 24 * 60 * 60 * 1000) {
    if (diff < 60 * 60 * 1000) {
      const minutes = Math.floor(diff / (60 * 1000));
      return `منذ ${minutes} دقيقة`;
    } else {
      const hours = Math.floor(diff / (60 * 60 * 1000));
      return `منذ ${hours} ساعة`;
    }
  }

  // Less than 7 days
  if (diff < 7 * 24 * 60 * 60 * 1000) {
    const days = Math.floor(diff / (24 * 60 * 60 * 1000));
    return `منذ ${days} يوم`;
  }

  // Format date
  return date.toLocaleDateString("ar-SA", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// Logout function
function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
  window.location.href = "/login";
}

// Auto-refresh every 5 minutes (only when tab is visible)
setInterval(() => {
  if (document.visibilityState === "visible") {
    cachedData.timestamp = 0; // Force refresh
    loadDashboardData();
  }
}, 5 * 60 * 1000);

// Performance monitoring
if (window.performance && window.performance.mark) {
  window.performance.mark("dashboard-script-loaded");
}
