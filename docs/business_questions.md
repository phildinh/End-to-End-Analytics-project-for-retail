# Business Questions — AdventureWorks Analytics

**Version:** 1.1
**Last updated:** 2026
**Author:** Phil Dinh

---

## Overview

Business questions driving the AdventureWorks analytics solution.

**Primary end user:** C-suite executives
**Report:** 4-page Power BI report — Executive Summary, Regional Map, Product Detail (drill-through), Customer Detail

---

## Core Business Questions

### 1. Is the business healthy?

> "Give me revenue, profit, orders, and return rate at a glance."

| | |
|---|---|
| **Metrics** | Total Revenue, Total Profit, Total Orders, Return Rate % |
| **Answered by** | Executive Summary — KPI cards |

---

### 2. Are we growing?

> "Show me how revenue is trending over time."

| | |
|---|---|
| **Metrics** | Monthly Revenue trend, MoM Revenue Δ, MoM Orders Δ |
| **Answered by** | Executive Summary — revenue trend line + MoM cards |

---

### 3. What is driving our orders and revenue?

> "Which products and categories matter most?"

| | |
|---|---|
| **Metrics** | Orders by Category, Top 10 Products by Orders / Revenue / Return % |
| **Answered by** | Executive Summary — bar chart + Top 10 table |

---

### 4. Where is the business performing?

> "Which markets and regions are strongest?"

| | |
|---|---|
| **Metrics** | Orders and Revenue by Country and Continent |
| **Answered by** | Regional Map — bubble map with continent filters |

---

### 5. How is a specific product tracking?

> "Drill into one product — are we hitting targets and is it profitable?"

| | |
|---|---|
| **Metrics** | Monthly Orders / Revenue / Profit vs Target, Total Profit vs Adjusted Profit |
| **Answered by** | Product Detail — drill-through from Top 10 table |

---

### 6. Who are our customers?

> "How many customers do we have, what is their value, and who are the top performers?"

| | |
|---|---|
| **Metrics** | Unique Customers, Revenue per Customer, Orders by Income Level and Occupation |
| **Answered by** | Customer Detail — KPI cards, trend line, donut charts, Top 100 table |

---

## Key Metrics

| Metric | Definition |
|---|---|
| Total Revenue | OrderQuantity × ProductPrice |
| Total Profit | OrderQuantity × (ProductPrice − ProductCost) |
| Total Orders | DISTINCTCOUNT(OrderNumber) |
| Return Rate % | Total Returns ÷ Total Orders |
| Revenue per Customer | Total Revenue ÷ Unique Customers |
| MoM Δ | Current month vs prior month via DATEADD |
| Adjusted Profit | Total Profit × (1 + Price Adjustment %) |