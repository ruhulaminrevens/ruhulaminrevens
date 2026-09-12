import json, math, os, platform, re, subprocess, tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

VERSION = "1.1.0"


def run(cmd, timeout=35):
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        cp = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=flags)
        return cp.returncode, cp.stdout.strip(), cp.stderr.strip()
    except Exception as e:
        return 99, "", str(e)


def ps(script, timeout=45):
    if os.name != "nt": return None, "Windows only"
    cmd = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",
           "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); $ProgressPreference='SilentlyContinue'; $ErrorActionPreference='Stop'; " + script + " | ConvertTo-Json -Depth 7 -Compress"]
    code,out,err = run(cmd,timeout)
    if code or not out: return None, err or out or "No data"
    try: return json.loads(out), ""
    except Exception as e: return None, f"JSON parse error: {e}"


def gb(v):
    try: return round(float(v)/(1024**3),1)
    except: return None


def num(v, default=None):
    try:
        value = float(v)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError): return default


def add(rows,cat,item,value,status="INFO",note="",weight=0,optional=False):
    rows.append(dict(category=cat,item=item,value=str(value),status=status,note=note,weight=float(weight),optional=optional))


def battery_grade(h):
    if h is None: return "—"
    return "A" if h>=90 else "B" if h>=80 else "C" if h>=70 else "D" if h>=60 else "F"


def parse_batteries(root):
    """Read installed batteries only, never capacity-history entries."""
    batteries = []
    for element in root.iter():
        if element.tag.split('}')[-1].lower() != 'battery':
            continue
        values = {e.tag.split('}')[-1].lower(): (e.text or '').strip()
                  for e in element}
        design = num(values.get('designcapacity'))
        full = num(values.get('fullchargecapacity'))
        valid = design is not None and design > 0 and full is not None and full >= 0
        health = full / design * 100 if valid else None
        batteries.append(dict(name=values.get('id') or f'Battery {len(batteries)+1}',
                              design=design, full=full, health=health,
                              cycles=values.get('cyclecount') or 'Not reported'))
    return batteries


def scan_battery(rows, summary):
    try:
        with tempfile.TemporaryDirectory(prefix='lcp_battery_') as temp_dir:
            path = Path(temp_dir) / 'battery.xml'
            code, out, err = run(['powercfg', '/batteryreport', '/output', str(path), '/xml'])
            if code or not path.exists():
                add(rows, 'Battery', 'Health', err or out or 'Unavailable', 'UNKNOWN',
                    'Battery health could not be measured', 12)
                return
            batteries = parse_batteries(ET.parse(path).getroot())
        summary['batteries'] = batteries
        valid = [b for b in batteries if b['health'] is not None]
        if not batteries or len(valid) != len(batteries):
            add(rows, 'Battery', 'Health', 'Unavailable or incomplete capacity data',
                'UNKNOWN', 'Verify all installed batteries manually', 12)
        else:
            health = sum(b['full'] for b in valid) / sum(b['design'] for b in valid) * 100
            grade = battery_grade(health)
            summary.update(battery_health=round(health, 1), battery_grade=grade)
            # A weak secondary battery must not disappear inside the combined average.
            worst = min(b['health'] for b in valid)
            status = 'PASS' if worst >= 80 else 'WARN' if worst >= 65 else 'FAIL'
            add(rows, 'Battery', 'Health', f'{health:.1f}% — Grade {grade}', status,
                'Combined capacity; status reflects weakest battery. 80%+ preferred.', 12)
        for battery in batteries:
            add(rows, 'Battery', battery['name'],
                f"Design {battery['design']} mWh | Full {battery['full']} mWh | Cycles {battery['cycles']}",
                note='Capacity can exceed the rated design value; runtime needs a physical test.')
    except Exception as error:
        add(rows, 'Battery', 'Health', error, 'UNKNOWN', 'Battery report could not be read', 12)


def scan_storage(rows,summary):
    script=r'''$o=@(); Get-PhysicalDisk | % { $d=$_; $r=$null; try{$r=$d|Get-StorageReliabilityCounter -ErrorAction Stop}catch{}; $o += [pscustomobject]@{FriendlyName=$d.FriendlyName;SerialNumber=$d.SerialNumber;MediaType=[string]$d.MediaType;BusType=[string]$d.BusType;HealthStatus=[string]$d.HealthStatus;OperationalStatus=($d.OperationalStatus -join ', ');Size=$d.Size;FirmwareVersion=$d.FirmwareVersion;Temperature=if($r){$r.Temperature}else{$null};Wear=if($r){$r.Wear}else{$null};PowerOnHours=if($r){$r.PowerOnHours}else{$null};ReadErrorsTotal=if($r){$r.ReadErrorsTotal}else{$null};WriteErrorsTotal=if($r){$r.WriteErrorsTotal}else{$null}} }; $o'''
    data,err=ps(script,55)
    if not data:
        add(rows,"Storage","Disk health",err or "Unavailable","UNKNOWN","Confirm with CrystalDiskInfo",15); summary["storage_status"]="UNKNOWN"; return
    disks=data if isinstance(data,list) else [data]; overall="PASS"
    for i,d in enumerate(disks,1):
        raw_health=d.get("HealthStatus")
        health={"0":"Healthy","1":"Warning","2":"Unhealthy","5":"Unknown"}.get(str(raw_health), str(raw_health) if raw_health is not None else "Unknown")
        st={"healthy":"PASS","warning":"WARN","unhealthy":"FAIL"}.get(health.lower(), "UNKNOWN")
        temp=num(d.get("Temperature")); rd=num(d.get("ReadErrorsTotal")); wr=num(d.get("WriteErrorsTotal"))
        reasons=[]
        if temp is not None and temp>=65:
            if st=="PASS": st="WARN"
            reasons.append(f"Hot {temp:.0f}°C")
        if (rd or 0)>0 or (wr or 0)>0:
            if st=="PASS": st="WARN"
            reasons.append("reported I/O errors")
        if {"PASS":0,"WARN":1,"UNKNOWN":2,"FAIL":3}[st] > {"PASS":0,"WARN":1,"UNKNOWN":2,"FAIL":3}[overall]: overall=st
        detail=f"{d.get('FriendlyName')} | {d.get('MediaType')}/{d.get('BusType')} | {gb(d.get('Size',0))} GB | {health}"
        add(rows,"Storage",f"Disk {i}",detail,st,"; ".join(reasons) or "Windows storage health",15/len(disks))
        add(rows,"Storage",f"Disk {i} serial",d.get("SerialNumber") or "Not reported")
        reli=[]
        if temp is not None: reli.append(f"Temp {temp:.0f}°C")
        if d.get("Wear") is not None: reli.append(f"Wear {d.get('Wear')} (vendor dependent)")
        if d.get("PowerOnHours") is not None: reli.append(f"Power-on {d.get('PowerOnHours')} h")
        reli += [f"Read errors {int(rd) if rd is not None else 'Not reported'}",f"Write errors {int(wr) if wr is not None else 'Not reported'}"]
        add(rows,"Storage",f"Disk {i} reliability"," | ".join(reli),note="Confirm SMART with CrystalDiskInfo")
    summary["storage_status"]=overall


def scan_devices(rows,summary):
    data,err=ps("Get-PnpDevice -PresentOnly | Select Class,FriendlyName,Status",55)
    ds=data if isinstance(data,list) else [data] if data else []
    
    specs={
      "Wi-Fi":(["wireless","wi-fi","802.11"],4,False),"Bluetooth":(["bluetooth"],3,False),
      "Camera":(["camera","webcam","integrated cam"],3,False),"Microphone":(["microphone","mic array","audio input"],2,False),
      "Audio":(["speaker","audio","sound"],2,False),"Fingerprint":(["fingerprint","biometric"],0,True),
      "Touchscreen":(["touch screen","touchscreen"],0,True),"Sensors":(["sensor","accelerometer","orientation"],0,True)}
    found={}
    for name,(keys,w,opt) in specs.items():
        matches=[device for device in ds if any(key in f"{device.get('Class','')} {device.get('FriendlyName','')}".lower() for key in keys)]
        ok=bool(matches); found[name]=ok
        healthy=ok and all(str(device.get('Status','')).lower()=='ok' for device in matches)
        status=('PASS' if healthy else 'WARN') if ok else ('INFO' if opt else 'UNKNOWN')
        add(rows,"Devices",name,"Detected" if healthy else "Detected; check device status" if ok else "Not detected",status,
            "Optional on some models" if opt else err or "Detection does not replace a functional test",w,opt)
    summary["devices"]=found


def auto_scan():
    rows=[]; summary={"manufacturer":"","model":"","cpu":"","serial":"","battery_health":None,"battery_grade":"—","storage_status":"INFO","devices":{}}
    add(rows,"OS","Windows",f"{platform.system()} {platform.release()} {platform.version()}")
    if os.name!="nt": add(rows,"OS","Compatibility","Windows 10/11 required","FAIL",weight=100); return rows,summary
    x,e=ps("Get-CimInstance Win32_ComputerSystem | Select Manufacturer,Model,TotalPhysicalMemory")
    if x:
        summary["manufacturer"]=x.get("Manufacturer") or ""; summary["model"]=x.get("Model") or ""; ram=gb(x.get("TotalPhysicalMemory",0))
        add(rows,"System","Manufacturer",summary["manufacturer"]); add(rows,"System","Model",summary["model"])
        add(rows,"Memory","Installed RAM",f"{ram} GB","PASS" if ram and ram>=16 else "WARN" if ram and ram>=8 else "FAIL","16 GB preferred; 8 GB minimum",8)
    x,e=ps("Get-CimInstance Win32_Processor | Select Name,NumberOfCores,NumberOfLogicalProcessors")
    if x:
        if isinstance(x,list): x=x[0]
        summary["cpu"]=x.get("Name") or ""; add(rows,"System","CPU",f"{summary['cpu']} | {x.get('NumberOfCores')}C/{x.get('NumberOfLogicalProcessors')}T","PASS",weight=5)
    x,e=ps("Get-CimInstance Win32_PhysicalMemory | Select Manufacturer,Capacity,ConfiguredClockSpeed,DeviceLocator")
    if x:
        for i,m in enumerate(x if isinstance(x,list) else [x],1): add(rows,"Memory",f"RAM module {i}",f"{gb(m.get('Capacity',0))} GB | {m.get('ConfiguredClockSpeed')} MHz | {m.get('Manufacturer') or 'Unknown'}")
    x,e=ps("Get-CimInstance Win32_BIOS | Select SMBIOSBIOSVersion,SerialNumber")
    if x:
        summary["serial"]=x.get("SerialNumber") or ""; add(rows,"BIOS","Version",x.get("SMBIOSBIOSVersion")); add(rows,"BIOS","Serial / Service Tag",summary["serial"],"PASS" if summary["serial"] else "WARN",weight=2)
    add(rows,"BIOS","Admin/System password","See manual BIOS test","INFO","Windows cannot reliably verify OEM BIOS passwords")
    scan_storage(rows,summary); scan_devices(rows,summary); scan_battery(rows,summary)
    add(rows,"Memory","RAM error test","Use Windows Memory Diagnostic if time permits","INFO","Restart required; not scored")
    required=[('Memory','Installed RAM',8),('System','CPU',5),('BIOS','Serial / Service Tag',2)]
    for category,item,weight in required:
        if not any(r['category']==category and r['item']==item for r in rows):
            add(rows,category,item,'Unavailable','UNKNOWN','Windows did not return this information',weight)
    return rows,summary


def factor(s): return {"PASS":1.0,"WARN":.55,"FAIL":0.0}.get(s)

def score(rows):
    vals=[(r["weight"],factor(r["status"])) for r in rows if r.get("weight",0)>0 and factor(r["status"]) is not None]
    d=sum(w for w,_ in vals); return round(sum(w*f for w,f in vals)/d*100) if d else 0

def completion(rows):
    a=[r for r in rows if r.get("weight",0)>0]; total=sum(r["weight"] for r in a)
    done=sum(r["weight"] for r in a if r["status"] in {"PASS","WARN","FAIL"}); return round(done/total*100) if total else 0

CRITICAL_MANUAL = {'Display Test', 'BIOS Password Check', 'Built-in Hardware Diagnostics'}


def recommendation(rows):
    s=score(rows); c=completion(rows)
    critical=any(r['status']=='FAIL' and (r['category']=='Storage' or r['item'] in CRITICAL_MANUAL) for r in rows)
    if critical:
        return 'REJECT', 'A critical storage/display/BIOS/diagnostics check failed.'
    required_auto = {('Memory','Installed RAM'), ('System','CPU'), ('Battery','Health')}
    missing_auto = any(not any((r['category'],r['item'])==key and factor(r['status']) is not None for r in rows)
                       for key in required_auto)
    storage=[r for r in rows if r['category']=='Storage' and r.get('weight',0)>0]
    missing_storage=not storage or any(factor(r['status']) is None for r in storage)
    missing_manual=any(not any(r['item']==item and factor(r['status']) is not None for r in rows)
                       for item in CRITICAL_MANUAL)
    if c<90 or missing_auto or missing_storage or missing_manual:
        return 'INCOMPLETE', 'Complete critical checks and at least 90% of weighted tests before deciding.'
    if s>=85 and not any(r['status']=='FAIL' for r in rows):
        return 'BUY', 'Strong tested condition. Check price, warranty and real battery runtime.'
    if s>=68:
        return 'NEGOTIATE', 'Warnings or failed checks need repair estimates and price negotiation.'
    return 'REJECT', 'Too many health concerns for a used-laptop purchase.'
