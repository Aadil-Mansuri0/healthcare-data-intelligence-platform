"""
Generates er_diagram.png — Entity Relationship diagram for the
Snowflake GOLD_SCHEMA (+ AUTH_SCHEMA) tables.
Run: python diagrams/generate_er_diagram.py
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(15, 10))
ax.set_xlim(0, 15)
ax.set_ylim(0, 10)
ax.axis("off")
fig.patch.set_facecolor("#0f172a")
ax.set_facecolor("#0f172a")

ax.text(7.5, 9.6, "Healthcare Data Warehouse — Entity Relationship Diagram",
        ha="center", fontsize=16, color="white", fontweight="bold")

def entity(x, y, w, h, title, fields, color="#0EA5E9"):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.08",
                          linewidth=1.8, edgecolor=color, facecolor="#1e293b")
    ax.add_patch(box)
    # Title bar
    title_box = FancyBboxPatch((x, y + h - 0.55), w, 0.55,
                                boxstyle="round,pad=0.02,rounding_size=0.08",
                                linewidth=0, facecolor=color)
    ax.add_patch(title_box)
    ax.text(x + w/2, y + h - 0.275, title, ha="center", va="center",
            color="white", fontsize=10.5, fontweight="bold")
    # Fields
    for i, f in enumerate(fields):
        fy = y + h - 0.85 - (i * 0.34)
        weight = "bold" if f.startswith("PK") or f.startswith("FK") else "normal"
        ax.text(x + 0.15, fy, f, ha="left", va="center",
                color="#e2e8f0", fontsize=8.3, fontweight=weight, family="monospace")
    return x, y, w, h

def relation(x1, y1, x2, y2, label=""):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-", mutation_scale=12,
                         color="#64748b", linewidth=1.3, linestyle="--")
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my, label, fontsize=7.5, color="#94a3b8",
                ha="center", va="center", backgroundcolor="#0f172a")

# ─── DRUG_SUMMARY ─────────────────────────────────────────────────────────────
entity(0.5, 5.7, 3.6, 3.4, "GOLD_SCHEMA.DRUG_SUMMARY", [
    "PK gnrc_name       STRING",
    "PK brnd_name       STRING",
    "PK year            INT",
    "   is_generic      BOOLEAN",
    "   total_claims    NUMBER",
    "   total_cost_usd  FLOAT",
    "   total_benes     NUMBER",
    "   avg_cost_/claim FLOAT",
    "   uniq_prescrbrs  NUMBER",
    "   cost_rank       INT",
], color="#eab308")

# ─── PRESCRIBER_SUMMARY ────────────────────────────────────────────────────────
entity(5.6, 5.3, 3.9, 3.8, "GOLD_SCHEMA.PRESCRIBER_SUMMARY", [
    "PK prscrbr_npi     NUMBER",
    "PK year            INT",
    "   last_org_name   STRING",
    "   first_name      STRING",
    "FK state_abrvtn    STRING(2)",
    "   prscrbr_type    STRING",
    "   city            STRING",
    "   total_claims    NUMBER",
    "   total_cost_usd  FLOAT",
    "   generic_rate    FLOAT",
    "   state_rank      INT",
], color="#22c55e")

# ─── STATE_KPI ────────────────────────────────────────────────────────────────
entity(10.9, 5.7, 3.6, 3.4, "GOLD_SCHEMA.STATE_KPI", [
    "PK state_abrvtn    STRING(2)",
    "PK year            INT",
    "   total_claims    NUMBER",
    "   total_cost_usd  FLOAT",
    "   total_benes     NUMBER",
    "   total_prscrbrs  NUMBER",
    "   uniq_drugs      NUMBER",
    "   cost_per_bene   FLOAT",
    "   national_rank   INT",
], color="#0ea5e9")

# ─── AUTH_SCHEMA.USERS ─────────────────────────────────────────────────────────
entity(0.5, 1.3, 3.6, 3.1, "AUTH_SCHEMA.USERS", [
    "PK username         STRING",
    "   email            STRING",
    "   full_name        STRING",
    "   hashed_password  STRING",
    "FK role              STRING",
    "   is_active        BOOLEAN",
    "   created_at       TIMESTAMP",
], color="#a855f7")

# ─── AUTH_SCHEMA.ROLES ─────────────────────────────────────────────────────────
entity(5.6, 1.3, 3.9, 2.3, "AUTH_SCHEMA.ROLES", [
    "PK role_name  STRING",
    "   description STRING",
    "   permissions ARRAY",
], color="#f43f5e")

# ─── AI_QUERY_LOG (audit trail) ────────────────────────────────────────────────
entity(10.9, 1.3, 3.6, 3.1, "AUDIT.AI_QUERY_LOG", [
    "PK query_id       STRING",
    "FK username        STRING",
    "   question        STRING",
    "   generated_sql   STRING",
    "   row_count       NUMBER",
    "   status          STRING",
    "   created_at      TIMESTAMP",
], color="#ef4444")

# ─── Relationships ──────────────────────────────────────────────────────────────
relation(4.4, 7.4, 5.6, 7.2, "gnrc_name (year)")
relation(9.5, 7.3, 10.9, 7.2, "state_abrvtn (year)")
relation(2.3, 4.4, 2.3, 4.4)  # placeholder spacing
relation(2.3, 1.3, 6.5, 2.3, "role")
relation(9.5, 2.5, 10.9, 2.8, "username")

plt.tight_layout()
plt.savefig("diagrams/er_diagram.png", dpi=150, facecolor="#0f172a", bbox_inches="tight")
print("✅ Saved diagrams/er_diagram.png")
