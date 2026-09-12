Laptop Check Pro v1.1.0 improves inspection reliability and report exports.

- Critical storage/display/BIOS/diagnostics failures now immediately produce REJECT.
- Missing critical tests and unknown hardware readings block a premature BUY recommendation.
- Windows disk health supports both numeric codes and text. Missing error counters show Not reported.
- Multiple installed batteries are measured separately. The weakest battery affects status.
- Scan failures recover the controls; manual results entered during scanning are preserved.
- New inspection reset, horizontal results scrolling, and keyboard unique-key feedback.
- HTML reports support printing / Save as PDF; JSON and Excel-friendly CSV are included.
- Versioned Windows ZIP, standalone EXE, and SHA256 checksums.

Download the Windows ZIP, extract it, and open LaptopCheckPro.exe. Python is not required. Windows x64 build; unsigned publisher. Existing v1.0.0 release remains available.

Automated regression and UI smoke checks run on Windows before publishing. Physical battery runtime, device functionality, display defects and BIOS state still require inspection on the actual laptop. English / Bengali dashboard retained; some technical details remain English.
