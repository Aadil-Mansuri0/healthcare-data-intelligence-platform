/**
 * Enterprise Healthcare Demo Database Seeder (Node.js 24 Native SQLite)
 * Populates demo/healthcare_demo.db with rich synthetic Medicare Part D data
 * across 2022, 2023, and 2024.
 */

const { DatabaseSync } = require("node:sqlite");
const path = require("node:path");
const fs = require("node:fs");

const DB_PATH = path.join(__dirname, "healthcare_demo.db");

if (fs.existsSync(DB_PATH)) {
  fs.unlinkSync(DB_PATH);
}

const db = new DatabaseSync(DB_PATH);

console.log("Creating tables in demo/healthcare_demo.db...");

db.exec(`
  DROP TABLE IF EXISTS drug_summary;
  DROP TABLE IF EXISTS prescriber_summary;
  DROP TABLE IF EXISTS state_kpi;

  CREATE TABLE drug_summary (
      gnrc_name TEXT,
      brnd_name TEXT,
      year INTEGER,
      is_generic INTEGER,
      total_claims INTEGER,
      total_cost_usd REAL,
      total_beneficiaries INTEGER,
      avg_cost_per_claim REAL,
      unique_prescribers INTEGER,
      cost_rank INTEGER
  );

  CREATE TABLE prescriber_summary (
      prscrbr_npi INTEGER,
      year INTEGER,
      prscrbr_last_org_name TEXT,
      prscrbr_first_name TEXT,
      prscrbr_state_abrvtn TEXT,
      prscrbr_type TEXT,
      prscrbr_city TEXT,
      total_claims INTEGER,
      total_cost_usd REAL,
      total_beneficiaries INTEGER,
      unique_drugs_prescribed INTEGER,
      generic_rate REAL,
      state_rank INTEGER
  );

  CREATE TABLE state_kpi (
      state_abrvtn TEXT,
      year INTEGER,
      total_claims INTEGER,
      total_cost_usd REAL,
      total_beneficiaries INTEGER,
      total_prescribers INTEGER,
      unique_drugs INTEGER,
      avg_cost_per_claim REAL,
      cost_per_beneficiary REAL,
      national_rank INTEGER,
      pain_specialty_claims INTEGER
  );
`);

const STATES = [
  "TX", "CA", "FL", "NY", "PA", "OH", "IL", "GA", "NC", "MI",
  "AZ", "WA", "TN", "MA", "IN", "MO", "MD", "WI", "CO", "MN"
];

const DRUGS = [
  { gnrc: "LISINOPRIL", brnd: "PRINIVIL", is_generic: 1, base_cost: 8.5 },
  { gnrc: "ATORVASTATIN", brnd: "LIPITOR", is_generic: 1, base_cost: 12.0 },
  { gnrc: "METFORMIN", brnd: "GLUCOPHAGE", is_generic: 1, base_cost: 6.0 },
  { gnrc: "AMLODIPINE", brnd: "NORVASC", is_generic: 1, base_cost: 9.0 },
  { gnrc: "OMEPRAZOLE", brnd: "PRILOSEC", is_generic: 1, base_cost: 10.5 },
  { gnrc: "LEVOTHYROXINE", brnd: "SYNTHROID", is_generic: 1, base_cost: 11.0 },
  { gnrc: "GABAPENTIN", brnd: "NEURONTIN", is_generic: 1, base_cost: 14.0 },
  { gnrc: "HYDROCHLOROTHIAZIDE", brnd: "MICROZIDE", is_generic: 1, base_cost: 7.5 },
  { gnrc: "SERTRALINE", brnd: "ZOLOFT", is_generic: 1, base_cost: 13.0 },
  { gnrc: "OXYCODONE", brnd: "OXYCONTIN", is_generic: 0, base_cost: 185.0 },
  { gnrc: "INSULIN GLARGINE", brnd: "LANTUS", is_generic: 0, base_cost: 320.0 },
  { gnrc: "ADALIMUMAB", brnd: "HUMIRA", is_generic: 0, base_cost: 5800.0 },
  { gnrc: "APIXABAN", brnd: "ELIQUIS", is_generic: 0, base_cost: 520.0 },
  { gnrc: "EMPAGLIFLOZIN", brnd: "JARDIANCE", is_generic: 0, base_cost: 580.0 },
  { gnrc: "SEMAGLUTIDE", brnd: "OZEMPIC", is_generic: 0, base_cost: 935.0 },
];

const SPECIALTIES = [
  "Family Medicine", "Internal Medicine", "Cardiology", "Endocrinology",
  "Pain Management", "Anesthesiology", "Psychiatry", "Nurse Practitioner"
];

const LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson", "Taylor", "Thomas", "Moore"];
const FIRST_NAMES = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth", "Sarah", "Priya", "Wei", "Aadil"];
const CITIES = { TX: "Austin", CA: "Sacramento", FL: "Miami", NY: "Albany", PA: "Philadelphia", OH: "Columbus", IL: "Chicago", GA: "Atlanta" };

const YEARS = [2022, 2023, 2024];

// Deterministic pseudo-random helper
let seed = 42;
function random() {
  seed = (seed * 9301 + 49297) % 233280;
  return seed / 233280;
}
function randInt(min, max) {
  return Math.floor(min + random() * (max - min + 1));
}
function choice(arr) {
  return arr[Math.floor(random() * arr.length)];
}

// 1. Seed drug summary
const insertDrug = db.prepare(`
  INSERT INTO drug_summary (gnrc_name, brnd_name, year, is_generic, total_claims, total_cost_usd, total_beneficiaries, avg_cost_per_claim, unique_prescribers, cost_rank)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);

for (const year of YEARS) {
  const yearDrugs = [];
  for (const d of DRUGS) {
    const claims = d.is_generic ? randInt(15000, 400000) : randInt(2500, 50000);
    const variance = 0.9 + random() * 0.2;
    const costPerClaim = Math.round(d.base_cost * variance * 100) / 100;
    const totalCost = Math.round(claims * costPerClaim * 100) / 100;
    const benes = Math.floor(claims * (0.6 + random() * 0.3));
    const prescribers = randInt(400, 15000);

    yearDrugs.push({
      gnrc: d.gnrc,
      brnd: d.brnd,
      year,
      is_generic: d.is_generic,
      claims,
      totalCost,
      benes,
      costPerClaim,
      prescribers
    });
  }

  yearDrugs.sort((a, b) => b.totalCost - a.totalCost);
  yearDrugs.forEach((d, idx) => {
    insertDrug.run(d.gnrc, d.brnd, d.year, d.is_generic, d.claims, d.totalCost, d.benes, d.costPerClaim, d.prescribers, idx + 1);
  });
}

// 2. Seed prescribers and state KPI
const insertPrescriber = db.prepare(`
  INSERT INTO prescriber_summary (prscrbr_npi, year, prscrbr_last_org_name, prscrbr_first_name, prscrbr_state_abrvtn, prscrbr_type, prscrbr_city, total_claims, total_cost_usd, total_beneficiaries, unique_drugs_prescribed, generic_rate, state_rank)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);

const insertState = db.prepare(`
  INSERT INTO state_kpi (state_abrvtn, year, total_claims, total_cost_usd, total_beneficiaries, total_prescribers, unique_drugs, avg_cost_per_claim, cost_per_beneficiary, national_rank, pain_specialty_claims)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);

let npiCounter = 1000000000;

for (const year of YEARS) {
  const stateAgg = {};
  for (const st of STATES) {
    stateAgg[st] = { claims: 0, cost: 0, benes: 0, prescribers: 0, painClaims: 0, rows: [] };
  }

  for (let i = 0; i < 600; i++) {
    npiCounter += randInt(1, 5);
    const state = choice(STATES);
    const specialty = choice(SPECIALTIES);
    const claims = randInt(100, 8000);
    const cost = Math.round(claims * (20 + random() * 380) * 100) / 100;
    const benes = Math.floor(claims * (0.5 + random() * 0.35));
    const uniqueDrugs = randInt(5, 25);
    const genericRate = Math.round((50 + random() * 42) * 10) / 10;
    const isPain = specialty === "Pain Management" || specialty === "Anesthesiology";

    const pRow = {
      npi: npiCounter,
      year,
      lastName: choice(LAST_NAMES),
      firstName: choice(FIRST_NAMES),
      state,
      specialty,
      city: CITIES[state] || "Metro Area",
      claims,
      cost,
      benes,
      uniqueDrugs,
      genericRate
    };

    stateAgg[state].rows.push(pRow);
    stateAgg[state].claims += claims;
    stateAgg[state].cost += cost;
    stateAgg[state].benes += benes;
    stateAgg[state].prescribers += 1;
    if (isPain) {
      stateAgg[state].painClaims += claims;
    }
  }

  // Insert prescribers with state rank
  for (const st of STATES) {
    const sObj = stateAgg[st];
    sObj.rows.sort((a, b) => b.cost - a.cost);
    sObj.rows.forEach((p, idx) => {
      insertPrescriber.run(
        p.npi, p.year, p.lastName, p.firstName, p.state, p.specialty,
        p.city, p.claims, p.cost, p.benes, p.uniqueDrugs, p.genericRate, idx + 1
      );
    });
  }

  // Insert state KPI with national rank
  const stateKeys = Object.keys(stateAgg);
  stateKeys.sort((a, b) => stateAgg[b].cost - stateAgg[a].cost);

  stateKeys.forEach((st, idx) => {
    const s = stateAgg[st];
    const avgCostPerClaim = s.claims > 0 ? Math.round((s.cost / s.claims) * 100) / 100 : 0;
    const costPerBene = s.benes > 0 ? Math.round((s.cost / s.benes) * 100) / 100 : 0;
    const uniqueDrugs = randInt(95, 145);

    insertState.run(
      st, year, s.claims, Math.round(s.cost * 100) / 100, s.benes,
      s.prescribers, uniqueDrugs, avgCostPerClaim, costPerBene, idx + 1, s.painClaims
    );
  });
}

console.log("✅ Seeded demo/healthcare_demo.db successfully!");
for (const table of ["drug_summary", "prescriber_summary", "state_kpi"]) {
  const row = db.prepare(`SELECT COUNT(*) as cnt FROM ${table}`).get();
  console.log(`   ${table.padEnd(20)} -> ${row.cnt} rows`);
}
db.close();
