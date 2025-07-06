// Dashboard JavaScript - Optimized for Offline-First

// Cache configuration
let cachedData = {};
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Initialize dashboard
document.addEventListener("DOMContentLoaded", function () {
  
  loadDashboardData();
  initializeChart();
});

// Optimized data loading with caching
async function loadDashboardData() {
  if (!window.token) return;

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
          headers: { Authorization: `Bearer ${window.token}` },
        }),
        fetch("/api/v1/employees/", {
          headers: { Authorization: `Bearer ${window.token}` },
        }),
        fetch("/api/v1/tasks/", {
          headers: { Authorization: `Bearer ${window.token}` },
        }),
        fetch("/api/v1/clients/", {
          headers: { Authorization: `Bearer ${window.token}` },
        }),
      ]
    );

   

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

// Lightweight chart initialization
function initializeChart() {
  const ctx = document.getElementById("projectsChart");
  if (!ctx || !window.Chart) return;

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["مكتملة", "قيد التنفيذ", "معلقة"],
      datasets: [
        {
          data: [45, 35, 20],
          backgroundColor: ["#48bb78", "#4299e1", "#ed8936"],
          borderWidth: 0,
          cutout: "65%",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 800,
        easing: "easeOutQuart",
      },
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            padding: 15,
            usePointStyle: true,
            font: { size: 11 },
          },
        },
      },
    },
  });
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
