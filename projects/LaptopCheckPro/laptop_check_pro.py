import json, os, platform, re, subprocess, tempfile, threading, webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_NAME = "Laptop Check Pro"
APP_VERSION = "0.1.0"
SYMBOL = {"PASS":"✅","WARN":"⚠️","FAIL":"❌","INFO":"ℹ️","MANUAL":"🧪"}


def run(cmd, timeout=30):
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=flags)
        return cp.returncode, cp.stdout.strip(), cp.stderr.strip()
    except Exception as e:
        return 99, "", str(e)


def ps(script, timeout=30):
    if os.name != "nt": return None, "Windows only"
    cmd = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",
           "$ErrorActionPreference='Stop'; " + script + " | ConvertTo-Json -Depth 5 -Compress"]
    code, out, err = run(cmd, timeout)
    if code or not out: return None, err or out or "No data"
    try: return json.loads(out), ""
    except Exception as e: return None, str(e)


def gb(n):
    try: return round(float(n)/(1024**3), 1)
    except: return None


def add(rows, cat, item, value, status="INFO", note=""):
    rows.append({"category":cat,"item":item,"value":str(value),"status":status,"note":note})


def battery(rows):
    p = Path(tempfile.gettempdir()) / "laptopcheck_battery.xml"
    code, out, err = run(["powercfg","/batteryreport","/output",str(p),"/xml"])
    if code or not p.exists():
        add(rows,"Battery","Battery report",err or out,"WARN"); return
    vals = {}
    try:
        for e in ET.parse(p).getroot().iter():
            tag = e.tag.split('}')[-1].lower(); txt = (e.text or '').strip()
            if txt and tag in {"designcapacity","fullchargecapacity","cyclecount"}: vals.setdefault(tag,txt)
        d = float(re.sub(r"[^0-9.]","",vals.get("designcapacity","0")))
        f = float(re.sub(r"[^0-9.]","",vals.get("fullchargecapacity","0")))
        h = (f/d*100) if d else 0
        s = "PASS" if h >= 80 else ("WARN" if h >= 70 else "FAIL")
        add(rows,"Battery","Health",f"{h:.1f}%",s,"80%+ preferred for used laptops")
        add(rows,"Battery","Capacity",f"Design {d:.0f} mWh | Full {f:.0f} mWh")
        if vals.get("cyclecount"): add(rows,"Battery","Cycle count",vals["cyclecount"])
    except Exception as e: add(rows,"Battery","Battery parse",e,"WARN")


def auto_scan():
    r=[]
    add(r,"OS","Windows",f"{platform.system()} {platform.release()} {platform.version()}")
    if os.name != "nt": add(r,"OS","Compatibility","Windows 10/11 required","FAIL"); return r

    x,e=ps("Get-CimInstance Win32_ComputerSystem | Select Manufacturer,Model,TotalPhysicalMemory")
    if x:
        add(r,"System","Manufacturer",x.get("Manufacturer")); add(r,"System","Model",x.get("Model"))
        ram=gb(x.get("TotalPhysicalMemory",0)); s="PASS" if ram and ram>=16 else ("WARN" if ram and ram>=8 else "FAIL")
        add(r,"Memory","Installed RAM",f"{ram} GB",s,"16 GB preferred")
    else: add(r,"System","Computer info",e,"WARN")

    x,e=ps("Get-CimInstance Win32_Processor | Select Name,NumberOfCores,NumberOfLogicalProcessors")
    if x:
        if isinstance(x,list): x=x[0]
        add(r,"System","CPU",f"{x.get('Name')} | {x.get('NumberOfCores')}C/{x.get('NumberOfLogicalProcessors')}T","PASS")
    else: add(r,"System","CPU",e,"WARN")

    x,e=ps("Get-CimInstance Win32_BIOS | Select SMBIOSBIOSVersion,SerialNumber")
    if x:
        add(r,"BIOS","Version",x.get("SMBIOSBIOSVersion")); add(r,"BIOS","Serial / Service Tag",x.get("SerialNumber"),"PASS")
        add(r,"BIOS","Admin/System password","Check manually in BIOS","MANUAL","Restart → F2/BIOS; password should not be set")
    else: add(r,"BIOS","BIOS info",e,"WARN")

    x,e=ps("Get-PhysicalDisk | Select FriendlyName,MediaType,HealthStatus,Size")
    if x:
        for i,d in enumerate(x if isinstance(x,list) else [x],1):
            hs=str(d.get("HealthStatus") or "Unknown"); s="PASS" if hs.lower()=="healthy" else "WARN"
            add(r,"Storage",f"Disk {i}",f"{d.get('FriendlyName')} | {d.get('MediaType')} | {gb(d.get('Size',0))} GB | {hs}",s,
                "Use CrystalDiskInfo for detailed SMART/wear")
    else: add(r,"Storage","Disk health",e,"WARN")

    x,e=ps("Get-PnpDevice -PresentOnly | Select Class,FriendlyName,Status")
    blob="\n".join(f"{z.get('Class','')} {z.get('FriendlyName','')} {z.get('Status','')}" for z in (x if isinstance(x,list) else [x] if x else [])).lower()
    checks={"Wi-Fi":["wireless","wi-fi","802.11"],"Bluetooth":["bluetooth"],"Camera":["camera","webcam"],
            "Fingerprint":["fingerprint","biometric"],"Touchscreen":["touch screen","touchscreen"],"Sensors":["sensor","accelerometer","orientation"]}
    for label,keys in checks.items():
        found=any(k in blob for k in keys); optional=label in {"Fingerprint","Touchscreen","Sensors"}
        add(r,"Devices",label,"Detected" if found else "Not detected","PASS" if found else ("INFO" if optional else "WARN"),"Optional on some models" if optional else "")
    battery(r)
    add(r,"Memory","RAM error test","Run Windows Memory Diagnostic","MANUAL","mdsched.exe requires restart")
    return r


def score(rows):
    pts={"PASS":100,"WARN":55,"FAIL":0}; x=[pts[z["status"]] for z in rows if z["status"] in pts]
    return round(sum(x)/len(x)) if x else 0


def verdict(n):
    return "EXCELLENT / BUY CANDIDATE" if n>=90 else "GOOD / BUY IF PRICE IS FAIR" if n>=80 else "CAUTION / RECHECK OR NEGOTIATE" if n>=65 else "HIGH RISK / AVOID"


def report(rows, manual, path):
    import html
    allrows=rows+manual; n=score(allrows)
    tr="".join(f"<tr><td>{html.escape(z['category'])}</td><td>{html.escape(z['item'])}</td><td>{html.escape(z['value'])}</td><td>{SYMBOL.get(z['status'],'')} {z['status']}</td><td>{html.escape(z['note'])}</td></tr>" for z in allrows)
    doc=f"""<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Laptop Check Report</title><style>body{{font-family:Segoe UI,Arial;background:#f4f7fb;padding:24px;color:#1f2937}}main{{max-width:1100px;margin:auto;background:white;padding:26px;border-radius:16px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #e5e7eb;padding:9px;text-align:left}}th{{background:#f8fafc}}.score{{font-size:38px;font-weight:800}}</style><main><h1>{APP_NAME}</h1><p>Generated {datetime.now():%Y-%m-%d %H:%M}</p><div class='score'>{n}/100</div><h2>{verdict(n)}</h2><table><tr><th>Category</th><th>Check</th><th>Result</th><th>Status</th><th>Note</th></tr>{tr}</table><p><b>Important:</b> Physical inspection is still required for hidden repairs, BIOS locks, intermittent ports, display defects and hinge quality.</p></main>"""
    Path(path).write_text(doc,encoding="utf-8")
    Path(path).with_suffix('.json').write_text(json.dumps({"app":APP_NAME,"version":APP_VERSION,"score":n,"verdict":verdict(n),"results":allrows},indent=2,ensure_ascii=False),encoding="utf-8")


class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(f"{APP_NAME} v{APP_VERSION}"); self.geometry("1040x700"); self.minsize(900,580)
        self.rows=[]; self.manual=[]; self.build()

    def build(self):
        top=ttk.Frame(self,padding=12); top.pack(fill="x")
        ttk.Label(top,text=APP_NAME,font=("Segoe UI",20,"bold")).pack(side="left")
        ttk.Button(top,text="Run Auto Scan",command=self.scan).pack(side="right",padx=4)
        ttk.Button(top,text="Export Report",command=self.export).pack(side="right",padx=4)
        nb=ttk.Notebook(self); nb.pack(fill="both",expand=True,padx=12,pady=(0,12))
        a=ttk.Frame(nb,padding=10); m=ttk.Frame(nb,padding=10); h=ttk.Frame(nb,padding=10)
        nb.add(a,text="1. Auto Scan"); nb.add(m,text="2. Manual Tests"); nb.add(h,text="3. Final Checks")
        self.bar=ttk.Progressbar(a,mode="indeterminate"); self.bar.pack(fill="x",pady=(0,8))
        cols=("category","item","value","status","note"); self.tree=ttk.Treeview(a,columns=cols,show="headings")
        for c,w in zip(cols,(100,170,280,90,300)): self.tree.heading(c,text=c.title()); self.tree.column(c,width=w,anchor="w")
        self.tree.pack(fill="both",expand=True); self.lbl=ttk.Label(a,text="Score: —",font=("Segoe UI",13,"bold")); self.lbl.pack(anchor="w",pady=8)
        ttk.Label(m,text="Guided physical tests",font=("Segoe UI",14,"bold")).pack(anchor="w")
        for title,cmd in [("Display Test",self.display),("Keyboard Test",self.keyboard),("Touch / 2-in-1 Test",self.touch),("Windows Memory Diagnostic",self.memory)]:
            ttk.Button(m,text=title,command=cmd,width=30).pack(anchor="w",pady=6)
        ttk.Button(m,text="Open CrystalDiskInfo",command=lambda:webbrowser.open("https://crystalmark.info/en/software/crystaldiskinfo/"),width=30).pack(anchor="w",pady=6)
        self.list=tk.Listbox(m,height=12); self.list.pack(fill="both",expand=True,pady=10)
        txt=tk.Text(h,wrap="word",font=("Segoe UI",11)); txt.pack(fill="both",expand=True)
        txt.insert("1.0","Final checks:\n\n• Dell: F2 BIOS → verify Admin/System password is NOT set.\n• Dell: F12 → Diagnostics → require ALL TESTS PASSED.\n• Battery: prefer 80%+ health.\n• Test USB-A, USB-C/Thunderbolt, HDMI, audio and charger.\n• Test Wi-Fi, Bluetooth, camera, mic and speakers.\n• 2-in-1: test Laptop → Tent → Stand → Tablet, touch and auto-rotation.\n• Inspect body, screws, hinge, display bezel and charging port.\n• Write exact model, CPU/RAM/SSD, service tag and warranty on invoice."); txt.config(state="disabled")

    def scan(self):
        self.bar.start(8); self.lbl.config(text="Scanning…"); [self.tree.delete(x) for x in self.tree.get_children()]
        threading.Thread(target=lambda:self.after(0,self.done,auto_scan()),daemon=True).start()
    def done(self,r):
        self.rows=r; self.bar.stop()
        for z in r: self.tree.insert("","end",values=(z["category"],z["item"],z["value"],f"{SYMBOL.get(z['status'],'')} {z['status']}",z["note"]))
        n=score(self.rows+self.manual); self.lbl.config(text=f"Score: {n}/100 — {verdict(n)}")
    def mark(self,item):
        ans=messagebox.askyesnocancel("Test result",f"Did {item} pass?\n\nYes = PASS | No = FAIL")
        if ans is None:return
        self.manual=[z for z in self.manual if z["item"]!=item]; add(self.manual,"Manual",item,"PASS" if ans else "FAIL","PASS" if ans else "FAIL")
        self.list.insert("end",f"{SYMBOL['PASS' if ans else 'FAIL']} {item}: {'PASS' if ans else 'FAIL'}")
    def display(self):
        w=tk.Toplevel(self); w.attributes('-fullscreen',True); colors=['black','white','red','green','blue','gray']; s={'i':0}; w.configure(bg=colors[0])
        def nxt(e=None):
            s['i']+=1
            if s['i']>=len(colors): w.destroy(); self.mark("Display Test")
            else:w.configure(bg=colors[s['i']])
        w.bind('<space>',nxt); w.bind('<Button-1>',nxt); w.bind('<Escape>',lambda e:(w.destroy(),self.mark("Display Test")))
    def keyboard(self):
        w=tk.Toplevel(self); w.title("Keyboard Test"); w.geometry("760x420"); tk.Text(w,font=("Consolas",12)).pack(fill="both",expand=True,padx=10,pady=10); ttk.Button(w,text="Finish",command=lambda:(w.destroy(),self.mark("Keyboard Test"))).pack(pady=8)
    def touch(self):
        w=tk.Toplevel(self); w.title("Touch Test"); w.geometry("800x540"); c=tk.Canvas(w,bg="white"); c.pack(fill="both",expand=True); last={'x':None,'y':None}
        c.bind('<Button-1>',lambda e:last.update(x=e.x,y=e.y)); c.bind('<B1-Motion>',lambda e:(c.create_line(last['x'],last['y'],e.x,e.y,width=4) if last['x'] is not None else None,last.update(x=e.x,y=e.y)))
        ttk.Button(w,text="Finish",command=lambda:(w.destroy(),self.mark("Touch / 2-in-1 Test"))).pack(pady=8)
    def memory(self):
        try: subprocess.Popen(["mdsched.exe"])
        except Exception as e: messagebox.showerror("Error",str(e))
    def export(self):
        p=filedialog.asksaveasfilename(defaultextension='.html',filetypes=[('HTML','*.html')],initialfile='Laptop_Check_Report.html')
        if p: report(self.rows,self.manual,p); messagebox.showinfo("Saved",f"HTML + JSON report saved.\n{p}")


if __name__ == "__main__": App().mainloop()
