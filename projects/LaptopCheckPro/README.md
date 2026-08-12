# Laptop Check Pro v1.0 Professional

**Laptop Check Pro** is a Windows 10/11 used-laptop inspection assistant designed to help buyers check a laptop in a few clicks before paying.

It combines automated Windows hardware checks with guided physical tests, then produces a weighted **0–100 health score**, **test completion percentage**, **Battery Grade**, and a final **BUY / NEGOTIATE / REJECT** recommendation.

## v1.0 highlights

- Professional dark dashboard UI
- English / বাংলা language toggle
- Weighted overall laptop health score
- Separate test-completion percentage
- Final **BUY / NEGOTIATE / REJECT** recommendation
- Battery health percentage + **Grade A/B/C/D/F**
- Detailed storage information through Windows `Get-PhysicalDisk` and `Get-StorageReliabilityCounter`
- SSD/HDD model, media/bus type, capacity, serial, temperature, power-on hours, wear counter when exposed by the driver, and reported read/write errors
- CPU, RAM total and RAM-module details
- BIOS version + serial/service tag
- Wi-Fi, Bluetooth, camera, microphone, audio, fingerprint, touchscreen and sensor detection
- Full-screen display color test
- Keyboard typing test
- Touchscreen drawing + 2-in-1 guidance
- Webcam test launcher
- Microphone test through Windows Sound settings
- Speaker beep test
- Ports + charger manual test
- Body + hinge inspection
- BIOS password guidance for Dell / HP / Lenovo
- Manufacturer built-in diagnostics guidance; Dell F12/ePSA highlighted
- Windows Memory Diagnostic launcher
- CrystalDiskInfo and HWiNFO quick links
- Professional HTML + JSON inspection report

## Battery grades

| Health | Grade | Buying interpretation |
|---|---|---|
| 90%+ | A | Excellent |
| 80–89% | B | Good / preferred |
| 70–79% | C | Usable; negotiate if needed |
| 60–69% | D | Weak; battery replacement risk |
| Below 60% | F | Poor |

Battery grading is based on Windows battery-report **Full Charge Capacity ÷ Design Capacity**.

## Recommendation logic

The app uses weighted results instead of treating every check equally.

- **BUY** — strong score, enough tests completed, and no critical display/storage/BIOS failure
- **NEGOTIATE** — usable laptop with warnings/wear that justify a lower price or more checks
- **REJECT** — low overall health or a critical failure
- **INCOMPLETE** — too many important manual tests are still pending

The recommendation is an inspection aid, not a guarantee.

## Recommended shop workflow

1. Open `LaptopCheckPro.exe`.
2. Click **Run Auto Scan**.
3. Review Battery Grade, Storage Health and detected hardware.
4. Run **Display Test** and **Keyboard Test**.
5. Test **Webcam, Microphone and Speaker**.
6. If touchscreen/2-in-1, run the touch test and physically check Laptop → Tent → Stand → Tablet plus auto-rotation.
7. Test USB-A, USB-C/Thunderbolt, HDMI, audio and charger.
8. Check the body, hinge, screws, bezel and repair/liquid signs.
9. Open BIOS and confirm Admin/System/Supervisor password is **not set**.
10. Run the manufacturer's built-in diagnostics. On Dell: **F12 → Diagnostics/ePSA** and require all tests to pass.
11. Export the HTML report and keep the service tag + warranty on the invoice.

## Storage-health note

Windows exposes different SMART/reliability fields depending on the SSD model, controller and driver. Laptop Check Pro therefore shows Windows-reported health plus available reliability counters, but does **not** treat the vendor-dependent `Wear` counter alone as a failure. Confirm detailed SMART data with **CrystalDiskInfo** before purchase when possible.

## Build the Windows EXE with GitHub Actions

1. Open the repository **Actions** tab.
2. Open **Build Laptop Check Pro EXE**.
3. Click **Run workflow**.
4. The workflow compiles all Python modules, runs a scoring smoke test, builds a single-file Windows EXE and generates SHA-256.
5. Download the **LaptopCheckPro-v1.0.0-Windows** artifact.
6. Extract and run `LaptopCheckPro.exe`.

## Source structure

```text
projects/LaptopCheckPro/
├── laptop_check_pro.py   # launcher
├── ui.py                 # dashboard + guided tests
├── core.py               # hardware scan + scoring/recommendation
├── reporting.py          # HTML + JSON reports
├── requirements-build.txt
├── README.md
└── LICENSE
```

## Important limitations

No Windows app can guarantee that a used laptop is defect-free. Software cannot reliably prove all BIOS password states, hidden motherboard repairs, liquid damage, intermittent ports, hinge quality, display defects or real-world battery runtime. Physical inspection remains mandatory.

## License

MIT — use, modify and distribute at your own risk.
