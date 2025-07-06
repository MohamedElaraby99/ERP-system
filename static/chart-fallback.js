// Chart.js fallback when CDN fails
window.Chart =
  window.Chart ||
  (function () {
    function Chart(ctx, config) {
      this.ctx = ctx;
      this.config = config;
      this.canvas = ctx.canvas || ctx;

      // Create a simple fallback chart
      this.render();
    }

    Chart.prototype.render = function () {
      if (!this.canvas) return;

      const canvas = this.canvas;
      const ctx = canvas.getContext("2d");
      const config = this.config;

      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Set canvas size
      canvas.width = 300;
      canvas.height = 300;

      if (config.type === "doughnut") {
        this.renderDoughnut(ctx, config);
      } else if (config.type === "bar") {
        this.renderBar(ctx, config);
      } else if (config.type === "line") {
        this.renderLine(ctx, config);
      } else {
        this.renderFallbackText(ctx);
      }
    };

    Chart.prototype.renderDoughnut = function (ctx, config) {
      const centerX = 150;
      const centerY = 150;
      const radius = 80;
      const innerRadius = 50;

      const data = config.data.datasets[0].data;
      const colors = config.data.datasets[0].backgroundColor;
      const labels = config.data.labels;

      let total = data.reduce((sum, val) => sum + val, 0);
      let currentAngle = -Math.PI / 2;

      // Draw segments
      data.forEach((value, index) => {
        const sliceAngle = (value / total) * 2 * Math.PI;

        ctx.beginPath();
        ctx.arc(
          centerX,
          centerY,
          radius,
          currentAngle,
          currentAngle + sliceAngle
        );
        ctx.arc(
          centerX,
          centerY,
          innerRadius,
          currentAngle + sliceAngle,
          currentAngle,
          true
        );
        ctx.closePath();

        ctx.fillStyle = colors[index] || "#ccc";
        ctx.fill();

        currentAngle += sliceAngle;
      });

      // Draw legend
      this.drawLegend(ctx, labels, colors, 20, 20);

      // Center text
      ctx.fillStyle = "#333";
      ctx.font = "14px Arial";
      ctx.textAlign = "center";
      ctx.fillText("إحصائيات", centerX, centerY);
    };

    Chart.prototype.renderBar = function (ctx, config) {
      const data = config.data.datasets[0].data;
      const labels = config.data.labels;
      const colors = config.data.datasets[0].backgroundColor;

      const chartArea = { x: 40, y: 40, width: 220, height: 200 };
      const barWidth = chartArea.width / data.length - 10;
      const maxValue = Math.max(...data);

      data.forEach((value, index) => {
        const barHeight = (value / maxValue) * chartArea.height;
        const x = chartArea.x + index * (barWidth + 10);
        const y = chartArea.y + chartArea.height - barHeight;

        ctx.fillStyle = colors[index] || "#007bff";
        ctx.fillRect(x, y, barWidth, barHeight);

        // Value text
        ctx.fillStyle = "#333";
        ctx.font = "12px Arial";
        ctx.textAlign = "center";
        ctx.fillText(value, x + barWidth / 2, y - 5);

        // Label
        ctx.fillText(
          labels[index],
          x + barWidth / 2,
          chartArea.y + chartArea.height + 20
        );
      });
    };

    Chart.prototype.renderLine = function (ctx, config) {
      const data = config.data.datasets[0].data;
      const labels = config.data.labels;

      const chartArea = { x: 40, y: 40, width: 220, height: 200 };
      const maxValue = Math.max(...data);
      const stepX = chartArea.width / (data.length - 1);

      ctx.strokeStyle = "#007bff";
      ctx.lineWidth = 2;
      ctx.beginPath();

      data.forEach((value, index) => {
        const x = chartArea.x + index * stepX;
        const y =
          chartArea.y +
          chartArea.height -
          (value / maxValue) * chartArea.height;

        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }

        // Draw points
        ctx.fillStyle = "#007bff";
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, 2 * Math.PI);
        ctx.fill();
      });

      ctx.stroke();
    };

    Chart.prototype.renderFallbackText = function (ctx) {
      ctx.fillStyle = "#666";
      ctx.font = "16px Arial";
      ctx.textAlign = "center";
      ctx.fillText("📊 الرسم البياني", 150, 140);
      ctx.font = "12px Arial";
      ctx.fillText("(وضع الطوارئ)", 150, 160);
    };

    Chart.prototype.drawLegend = function (ctx, labels, colors, x, y) {
      ctx.font = "12px Arial";
      ctx.textAlign = "left";

      labels.forEach((label, index) => {
        const legendY = y + index * 20;

        // Color box
        ctx.fillStyle = colors[index] || "#ccc";
        ctx.fillRect(x, legendY, 12, 12);

        // Label text
        ctx.fillStyle = "#333";
        ctx.fillText(label, x + 20, legendY + 10);
      });
    };

    return Chart;
  })();

// Register Chart.js globally
if (typeof window !== "undefined") {
  window.Chart = window.Chart;
}


