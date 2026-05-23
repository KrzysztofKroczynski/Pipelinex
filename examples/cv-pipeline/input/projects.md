# Projects

## OpenBudget — Personal Finance Tracker
**2024** | github.com/alexrivera/openbudget

Open-source web app for tracking personal finances across multiple accounts.
Connects to bank exports via CSV/OFX, categorises transactions automatically
using a small ML classifier, and generates monthly spending reports.

Used by ~300 people based on GitHub stars and issue activity.

**Tech:** Python, FastAPI, React, PostgreSQL, Docker

---

## Logpipe — Structured Log Aggregator
**2023** | github.com/alexrivera/logpipe

CLI tool that tails multiple log sources, parses structured fields, and
streams them into a unified view with filtering. Handles JSON logs, nginx
access logs, and plain text with regex patterns.

**Tech:** Python, Click, Rich

---

## Compliance Automation Suite
**2021** | Internal tool at Finova GmbH

Workflow automation for the compliance team — pulls transaction data from
three internal systems, cross-references against watchlists, and flags
anomalies for review. Replaced a manual process that took a team of 3
analysts two days per week.

**Tech:** Python, PostgreSQL, Airflow, React
