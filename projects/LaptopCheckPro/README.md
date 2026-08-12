# Laptop Check Pro

A lightweight Windows 10/11 used-laptop inspection assistant. It automates what Windows can reliably expose, then guides the buyer through the physical tests that still need human eyes/hands.

## What it checks automatically

- Manufacturer / exact model
- CPU model, cores and threads
- Installed RAM
- Physical disk type / Windows-reported health
- Battery design capacity, full-charge capacity and health percentage via `powercfg /batteryreport /xml`
- BIOS version + serial/service tag
- Wi-Fi, Bluetooth, camera, fingerprint, touchscreen and sensors detection
- Pass / Warning / Fail scoring
- HTML + JSON report export

## Guided manual tests

- Full-screen display color test
- Keyboard typing test
- Touchscreen drawing test
- 360° / tent / stand / tablet mode check
- Auto-rotation / sensor check
- Windows Memory Diagnostic launcher
- Dell F2 BIOS reminder
- Dell F12 ePSA diagnostics reminder
- Ports, charger, camera, microphone, speaker and hinge/body checklist

## Important limitations

No Windows app can guarantee a used laptop is defect-free. BIOS/Admin passwords, hidden motherboard repairs, liquid damage, intermittent ports, display defects, hinge quality and real battery runtime still need physical inspection.

## Build the EXE with GitHub Actions

1. Open the repository **Actions** tab.
2. Open **Build Laptop Check Pro EXE**.
3. Click **Run workflow**.
4. When the job completes, download the **LaptopCheckPro-Windows** artifact.
5. Extract and run `LaptopCheckPro.exe` on the laptop you want to inspect.

## Recommended shop flow

1. Run **Auto Scan**.
2. Prefer battery health **80%+**.
3. Run **Display Test**.
4. Run **Keyboard Test**.
5. If touch/2-in-1: run **Touch Test** and physically test Laptop → Tent → Stand → Tablet.
6. Restart Dell → **F2** and verify BIOS/Admin password is not set.
7. Restart Dell → **F12 → Diagnostics** and require all tests to pass.
8. Test USB, USB-C/Thunderbolt, HDMI, audio, Wi-Fi, Bluetooth, camera, mic and speakers.
9. Export the HTML report and save the service tag + warranty on the invoice.

## License

MIT — use, modify and distribute at your own risk.
