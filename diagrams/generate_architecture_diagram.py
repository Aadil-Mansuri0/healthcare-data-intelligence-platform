"""
Generates architecture_diagram.png — full system architecture visualization.
Run: python diagrams/generate_architecture_diagram.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

fig, ax = plt.subplots(figsize=(16, 11))
ax.set_xlim(0, 16)
ax.set_ylim(0, 11)
ax.axis("off")
fig.patch.set_facecolor("#0f172a")
ax.set_facecolor("#0f172a")

def box(x, y, w, h, text, color="#0EA5E9", text_color="white", fontsize=9.5):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.08,rounding_size=0.12",
        linewidth=1.5, edgecolor=color, facecolor=color + "33",
    )
    ax.add_patch(rect)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
             color=text_color, fontsize=fontsize, fontweight="bold", wrap=True)
    return (x + w/2, y, x + w/2, y + h)

def arrow(x1, y1, x2, y2, color="#64748b"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=15,
                         color=color, linewidth=1.5)
    ax.add_patch(a)

# Title
ax.text(8, 10.5, "Healthcare Data Intelligence Platform — Architecture",
        ha="center", fontsize=17, color="white", fontweight="bold")

# Source
box(6.5, 9.2, 3, 0.7, "PostgreSQL\n(Medicare Part D Source)", color="#F97316")

# Bronze/Silver/Gold
box(1, 7.5, 3, 0.9, "BRONZE\nS3 Raw Parquet", color="#a16207")
box(6.5, 7.5, 3, 0.9, "SILVER\nCleaned & Validated", color="#94a3b8")
box(12, 7.5, 3, 0.9, "GOLD\nAggregated KPIs", color="#eab308")

# Validation
box(6.5, 6.2, 3, 0.7, "Great Expectations +\nAI Data Quality Checker", color="#ef4444")

# Snowflake
box(6, 4.9, 4, 0.8, "Snowflake Data Warehouse\n(GOLD_SCHEMA)", color="#38bdf8")

# Airflow orchestration (side)
box(0.3, 4.9, 2.8, 0.8, "Apache Airflow\nOrchestration", color="#dc2626")

# FastAPI + Auth
box(2, 3.4, 3.5, 0.9, "FastAPI Backend\nJWT Auth + RBAC", color="#22c55e")

# AI Services
box(6.2, 3.4, 3.8, 0.9, "AI Services\nNL2SQL · Insights · Reports\nQuality Checker · Recs", color="#a855f7")

# Monitoring
box(10.5, 3.4, 3, 0.9, "Monitoring\nPrometheus + Grafana", color="#f43f5e")

# Frontend + PowerBI
box(2, 1.9, 3.5, 0.9, "Next.js Dashboard\n+ AI Chat UI", color="#0ea5e9")
box(6.2, 1.9, 3.5, 0.9, "Power BI\nExecutive Dashboard", color="#eab308")

# Docker/CI-CD footer
box(2, 0.5, 8, 0.7, "Docker + Docker Compose   |   GitHub Actions CI/CD   |   AWS (S3, IAM, EC2)",
    color="#64748b", fontsize=9)

# Arrows
arrow(8, 9.2, 2.5, 8.4)     # source -> bronze
arrow(8, 9.2, 8, 8.4)       # source -> silver
arrow(2.5, 7.5, 8, 8.15)    # bronze -> silver (flow)
arrow(9.5, 7.9, 12, 7.9)    # silver -> gold
arrow(8, 7.5, 8, 6.9)       # silver -> validation
arrow(8, 6.2, 8, 5.7)       # validation -> snowflake
arrow(13.5, 7.5, 8.5, 5.4)  # gold -> snowflake
arrow(1.7, 4.9, 6, 5.2)     # airflow -> snowflake (orchestrates)
arrow(8, 4.9, 3.7, 4.3)     # snowflake -> fastapi
arrow(8, 4.9, 8, 4.3)       # snowflake -> ai services
arrow(3.7, 3.4, 3.7, 2.8)   # fastapi -> nextjs
arrow(8, 4.9, 11, 4.3)      # snowflake -> powerbi (direct)
arrow(4.5, 3.4, 6.2, 3.4, color="#a855f7")  # fastapi <-> ai services

plt.tight_layout()
plt.savefig("diagrams/architecture_diagram.png", dpi=150, facecolor="#0f172a", bbox_inches="tight")
print("✅ Saved diagrams/architecture_diagram.png")
