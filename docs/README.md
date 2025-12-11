# NBA ELO Engine - Documentation Index

This directory contains all project documentation organized by category.

## Quick Links

- [Main README](../README.md) - Project overview and quickstart
- [Production Readiness Assessment](reports/PRODUCTION_READINESS_ASSESSMENT.md) - Current production status
- [Enhanced Features Success Report](reports/ENHANCED_FEATURES_SUCCESS.md) - Phase 1.6 implementation results

## Documentation Structure

### Core Documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture and design
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Technical overview
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Common commands and operations
- [CHANGELOG.md](CHANGELOG.md) - Version history

### Checkpoints
- [checkpoints/](checkpoints/) - Project checkpoints and session saves
  - CHECKPOINT_DECEMBER_2_2025.md
  - CHECKPOINT_DECEMBER_2_2025_FINAL.md
  - CHECKPOINT_DECEMBER_2_2025_SESSION_2.md
  - CHECKPOINT_NEWSLETTER_VIZ_INTEGRATION.md
  - CHECKPOINT_PHASE_3.md

### Implementation Plans
- [plans/](plans/) - Feature planning and roadmaps
  - PHASE_3_COMPLETE.md
  - PHASE_4_PLAN.md
  - PHASE_4D_BPM_PLAN.md
  - PHASE_2_BETTING_MARKET_PLAN.md
  - PLAYER_ELO_INTEGRATION_PLAN.md
  - NBA_INSIGHTS_IMPROVEMENTS_ROADMAP.md

### Analysis & Reports
- [reports/](reports/) - Backtesting, analysis, and validation reports
  - PRODUCTION_READINESS_ASSESSMENT.md - **Current production status**
  - ENHANCED_FEATURES_SUCCESS.md - Form + rest implementation
  - HYBRID_ELO_BACKTEST_ANALYSIS.md - Why player ELO failed
  - RUDY_GOBERT_ELO_ANALYSIS.md - Position scaling fix
  - MOV_BACKTEST_RESULTS.md - Margin of victory validation
  - POINT_DIFFERENTIAL_ANALYSIS.md
  - PLAYER_H2H_BACKTEST_RESULTS.md
  - PHASE_2_BETTING_MARKET_RESULTS.md
  - BPM_VALIDATION_REPORT.md
  - CODEBASE_AUDIT_REPORT.md
  - MODEL_IMPROVEMENTS_ANALYSIS.md
  - NBA_INSIGHTS_ANALYSIS.md

### Completed Features
- [completed/](completed/) - Feature completion logs
  - SCRAPER_COMPLETE.md
  - NBA_API_INTEGRATION_COMPLETE.md
  - ADMIN_APP_COMPLETE.md
  - NEWSLETTER_PREMIUM_COMPLETE.md
  - IMPLEMENTATION_COMPLETE.md
  - SYSTEM_FIXES_COMPLETE.md
  - ELO_FIX_VERIFICATION_COMPLETE.md
  - INJURY_AND_ELO_FIXES_COMPLETE.md
  - CRITICAL_FEATURES_COMPLETE.md
  - CRITICAL_FIXES_COMPLETE.md
  - CRITICAL_ISSUES_RESOLVED.md
  - ISSUES_RESOLVED_BATCH_3.md
  - And more...

### Newsletter & Workflow
- [NEWSLETTER_WORKFLOW.md](NEWSLETTER_WORKFLOW.md) - Newsletter generation process
- [DAILY_NEWSLETTER_WORKFLOW.md](DAILY_NEWSLETTER_WORKFLOW.md) - Daily workflow
- [QA_REPORT_PREMIUM_NEWSLETTER.md](QA_REPORT_PREMIUM_NEWSLETTER.md) - QA process
- [NEWSLETTER_ISSUES_AND_TASKS.md](NEWSLETTER_ISSUES_AND_TASKS.md)
- [NEWSLETTER_VISUALIZATION_IDEAS.md](NEWSLETTER_VISUALIZATION_IDEAS.md)
- [NEWSLETTER_VIZ_VALIDATION.md](NEWSLETTER_VIZ_VALIDATION.md)
- [DASHBOARD_FRAMEWORK.md](DASHBOARD_FRAMEWORK.md)

### Guide & Reference
- [ADMIN_TOOL_GUIDE.md](completed/ADMIN_TOOL_GUIDE.md) - Admin dashboard usage

## Current System Status

**Version**: Phase 1.6 (Enhanced Features)
**Prediction Accuracy**: 65.93% (31,211 games, 2000-2025)
**Status**: Production Ready (95% complete)

**Key Features**:
- Team ELO with Margin of Victory (MOV)
- Form factor tracking (last 5 games)
- Rest penalties (back-to-back, 1-day rest)
- Player ratings with position scaling
- Injury impact analysis
- Automated daily updates
- Web dashboard with predictions

## Recent Updates

**December 2, 2025**:
- Enhanced features deployed (form + rest)
- Position scaling applied to player ratings (Rudy Gobert fix)
- Active NBA teams filter (30 teams)
- Production readiness assessment completed
- Documentation reorganized into docs/ folder

## See Also

- [Main README](../README.md) - Getting started guide
- [scripts/](../scripts/) - Automation scripts
- [src/](../src/) - Source code
- [data/](../data/) - Data files and exports
- [newsletters/](../newsletters/) - Generated newsletters
