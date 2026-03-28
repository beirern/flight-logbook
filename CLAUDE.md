# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A single-user Django flight logbook application for tracking flight time, currency status, and license progress per FAA regulations. Uses Django templates with Bootstrap 5 and Chart.js for visualization.

## Commands

```bash
# Local development
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver        # http://localhost:8000/

# Docker development
./start.sh                        # builds and runs web + PostgreSQL via docker-compose

# Tests (currently empty stubs)
python manage.py test

# No linter or formatter configured
```

## Architecture

**Django multi-app structure** with domain-driven apps: `flights` (core), `pilots`, `planes`, `routes`, `licenses`, `medicals`.

**Single-user design**: All views hardcode `Pilot.objects.get(pk=1)` — there is no auth/multi-user system.

**Key files:**
- `flights/views/dashboard_views.py` — all page views (dashboard, logbook, routes_map, aircraft, people)
- `flights/utils/currency_calculator.py` — FAR 61.57(a) passenger currency (90-day landing window), medical status, license progress
- `flights/utils/statistics.py` — time aggregations, monthly progressions, breakdowns for charts
- `flights/admin.py` — admin customizations with inline approach editing
- `flights/urls.py` — all URL routing

**URL routes**: `/` (dashboard), `/logbook/`, `/routes/`, `/people/`, `/aircraft/`, `/admin/`

**Frontend pattern**: Views serialize data to JSON in context, templates consume it with Chart.js via `{{ data|safe }}`. All templates extend `flights/templates/flights/base.html`.

**Data model**: Flight is the core record linking to Pilot, Plane, Route, and Approach (inline). Route uses a through model (RouteWaypoint) for ordered airport sequences. Routes view calculates great-circle distances via Haversine in nautical miles.

## Deployment

GitHub Actions (`.github/workflows/deploy.yml`) builds a Docker image on push to `main`, pushes to AWS ECR, and deploys to AWS Lightsail via SSH with `docker compose up -d`.

**Stack**: Python 3.13-slim, Gunicorn, PostgreSQL 18, WhiteNoise for static files.
