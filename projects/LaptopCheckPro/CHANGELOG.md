# Version history

## 1.1.0 — 2026-09-12

### Fixed
- Storage health enum/string interpretation; Unhealthy now FAIL, not WARN.
- Unknown storage counters no longer appear as zero errors.
- Critical failures take precedence over incomplete test coverage.
- BUY requires critical manual tests, required automatic readings, 90% weighted completion and no failed checks.
- Missing CPU/RAM/serial data remains visible in completion coverage.
- PnP detection checks device status; detection alone does not prove functionality.
- Installed-battery XML parsing, missing versus zero capacity, temporary report cleanup and multiple batteries.
- Main-thread UI queue prevents worker threads from touching Tk; scan failure restores controls.
- Manual results entered during a scan survive completion; changed serial resets old manual results.
- Report HTML escaping, CSV formula neutralization and visible export errors.

### Added
- New inspection reset.
- Horizontal table scrollbar and unique keyboard-key counter.
- Excel-friendly UTF-8 CSV export and print styling for HTML reports.
- Regression suite, source UI smoke test and packaged EXE smoke test.
- Versioned Windows ZIP with documentation, license and checksums.
- Release workflow derives version from source and does not overwrite previous releases.

## 1.0.0 — 2026-08-12

Existing GitHub baseline: English/Bengali dashboard, automated hardware checks,
battery grading, guided manual tests, weighted scoring and HTML/JSON reports.
