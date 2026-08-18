"""
Generates pipeline_diagram.png — Airflow DAG execution flow visualization.
Run: python diagrams/generate_pipeline_diagram.py
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(16, 6))
ax.set_xlim(0, 16)
ax.set_ylim(0, 6)
ax.axis("off")
fig.patch.set_facecolor("#0f172a")
ax.set_facecolor("#0f172a")

ax.text(8, 5.5, "Airflow DAG: healthcare_medallion_pipeline (daily 2:00 AM IST)",
        ha="center", fontsize=14.5, color="white", fontweight="bold")

steps = [
    ("check_source", "Verify\nPostgreSQL", "#64748b"),
    ("bronze_ingestion", "Bronze\nIngestion\n(Spark)", "#a16207"),
    ("validate_bronze", "GE Suite +\nAI Quality\nCheck", "#ef4444"),
    ("silver_transformation", "Silver\nTransform\n(Spark)", "#94a3b8"),
    ("gold_aggregation", "Gold\nAggregation\n(Spark)", "#eab308"),
    ("snowflake_load", "Load to\nSnowflake\n(COPY INTO)", "#38bdf8"),
    ("notify_success", "Notify\nSuccess", "#22c55e"),
]

n = len(steps)
box_w, box_h = 1.7, 1.6
gap = (16 - n * box_w) / (n + 1)
y = 2.3

centers = []
for i, (task_id, label, color) in enumerate(steps):
    x = gap + i * (box_w + gap)
    rect = FancyBboxPatch((x, y), box_w, box_h,
                           boxstyle="round,pad=0.06,rounding_size=0.1",
                           linewidth=1.8, edgecolor=color, facecolor=color + "33")
    ax.add_patch(rect)
    ax.text(x + box_w/2, y + box_h/2 + 0.15, label, ha="center", va="center",
            color="white", fontsize=8.8, fontweight="bold")
    ax.text(x + box_w/2, y - 0.25, task_id, ha="center", va="center",
            color="#94a3b8", fontsize=7, family="monospace")
    centers.append((x + box_w/2, y, x + box_w, y + box_h/2))

# Arrows between consecutive steps
for i in range(n - 1):
    x1 = gap + i * (box_w + gap) + box_w
    x2 = gap + (i + 1) * (box_w + gap)
    yc = y + box_h / 2
    arrow = FancyArrowPatch((x1, yc), (x2, yc), arrowstyle="-|>",
                             mutation_scale=16, color="#0EA5E9", linewidth=2)
    ax.add_patch(arrow)

# Retry / failure annotation
ax.text(8, 0.7, "Each task: 2 retries, 5 min delay | Critical GE/validation failure halts pipeline & alerts via email",
        ha="center", fontsize=9, color="#94a3b8", style="italic")

# Trigger annotation for data_quality_ge_suite DAG
ax.annotate("", xy=(gap + 2 * (box_w + gap) + box_w/2, y + box_h + 0.05),
            xytext=(gap + 2 * (box_w + gap) + box_w/2, y + box_h + 0.55),
            arrowprops=dict(arrowstyle="-|>", color="#ef4444", linewidth=1.5))
ax.text(gap + 2 * (box_w + gap) + box_w/2, y + box_h + 0.7,
        "data_quality_ge_suite DAG\n(Great Expectations)", ha="center", fontsize=7.5,
        color="#ef4444", fontweight="bold")

plt.tight_layout()
plt.savefig("diagrams/pipeline_diagram.png", dpi=150, facecolor="#0f172a", bbox_inches="tight")
print("✅ Saved diagrams/pipeline_diagram.png")
