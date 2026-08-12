import json, os, platform, re, subprocess, tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

VERSION = "1.0.0"


def run(cmd, timeout=35):
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=flags)
        return cp.returncode, cp.stdout.strip(), cp.stderr.strip()
    except Exception as e:
        return 99, "", str(e)


def ps(script, timeout=45):
    if os.name != "nt": return None, "Windows only"
    cmd = ["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",
           "$ProgressPreference='SilentlyContinue'; $ErrorActionPreference='Stop'; " + script + " | ConvertTo-Json -Depth 7 -Compress"]
    code,out,err = run(cmd,timeout)
    if code or not out: return None, err or out or "No data"
    try: return json.loads(out), ""
    except Exception as e: return None, f"JSON parse error: {e}"


def gb(v):
    try: return round(float(v)/(1024**3),1)
    except: return None


def num(v, default=None):
    try: return float(v)
    except: return default


def add(rows,cat,item,value,status="INFO",note="",weight=0,optional=False):
    rows.append(dict(category=cat,item=item,value=str(value),status=status,note=note,weight=float(weight),optional=optional))


def battery_grade(h):
    if h is None: return "—"
    return "A" if h>=90 else "B" if h>=80 else "C" if h>=70 else "D" if h>=60 else "F"


def scan_battery(rows,summary):
    p=Path(tempfile.gettempdir())/"lcp_battery.xml"
    code,out,err=run(["powercfg","/batteryreport","/output",str(p),"/xml"])
    if code or not p.exists():
        add(rows,"Battery","Battery report",err or out or "Unavailable","WARN",weight=12); return
    try:
        vals={}
        for e in ET.parse(p).getroot().iter():
            tag=e.tag.split('}')[-1].lower(); text=(e.text or '').strip()
            if text and tag in {"designcapacity","fullchargecapacity","cyclecount"}: vals.setdefault(tag,text)
        d=num(re.sub(r"[^0-9.]","",vals.get("designcapacity","")),0); f=num(re.sub(r"[^0-9.]","",vals.get("fullchargecapacity","")),0)
        h=f/d*100 if d else None; g=battery_grade(h)
        summary.update(battery_health=round(h,1) if h is not None else None,battery_grade=g)
        st="PASS" if h is not None and h>=80 else "WARN" if h is None or h>=65 else "FAIL"
        add(rows,"Battery","Health",f"{h:.1f}% — Grade {g}" if h is not None else "Unknown",st,"80%+ preferred",12)
        add(rows,"Battery","Capacity",f"Design {d:.0f} mWh | Full {f:.0f} mWh")
        if vals.get("cyclecount"): add(rows,"Battery","Cycle count",vals["cyclecount"],note="Health matters more than cycle count")
    except Exception as e: add(rows,"Battery","Battery parse",e,"WARN",weight=12)


def scan_storage(rows,summary):
    script=r'''$o=@(); Get-PhysicalDisk | % { $d=$_; $r=$null; try{$r=$d|Get-StorageReliabilityCounter -ErrorAction Stop}catch{}; $o += [pscustomobject]@{FriendlyName=$d.FriendlyName;SerialNumber=$d.SerialNumber;MediaType=$d.MediaType;BusType=$d.BusType;HealthStatus=$d.HealthStatus;OperationalStatus=($d.OperationalStatus -join ', ');Size=$d.Size;FirmwareVersion=$d.FirmwareVersion;Temperature=if($r){$r.Temperature}else{$null};Wear=if($r){$r.Wear}else{$null};PowerOnHours=if($r){$r.PowerOnHours}else{$null};ReadErrorsTotal=if($r){$r.ReadErrorsTotal}else{$null};WriteErrorsTotal=if($r){$r.WriteErrorsTotal}else{$null}} }; $o'''
    data,err=ps(script,55)
    if not data:
        add(rows,"Storage","Disk health",err or "Unavailable","WARN","Confirm with CrystalDiskInfo",15); summary["storage_status"]="WARN"; return
    disks=data if isinstance(data,list) else [data]; overall="PASS"
    for i,d in enumerate(disks,1):
        health=str(d.get("HealthStatus") or "Unknown"); st="PASS" if health.lower()=="healthy" else "WARN"
        temp=num(d.get("Temperature")); rd=num(d.get("ReadErrorsTotal"),0) or 0; wr=num(d.get("WriteErrorsTotal"),0) or 0
        reasons=[]
        if temp is not None and temp>=65: st="WARN"; reasons.append(f"Hot {temp:.0f}°C")
        if rd>0 or wr>0: st="WARN"; reasons.append("reported I/O errors")
        if st=="WARN" and overall!="FAIL": overall="WARN"
        detail=f"{d.get('FriendlyName')} | {d.get('MediaType')}/{d.get('BusType')} | {gb(d.get('Size',0))} GB | {health}"
        add(rows,"Storage",f"Disk {i}",detail,st,"; ".join(reasons) or "Windows storage health",15/len(disks))
        add(rows,"Storage",f"Disk {i} serial",d.get("SerialNumber") or "Not reported")
        reli=[]
        if temp is not None: reli.append(f"Temp {temp:.0f}°C")
        if d.get("Wear") is not None: reli.append(f"Wear {d.get('Wear')} (vendor dependent)")
        if d.get("PowerOnHours") is not None: reli.append(f"Power-on {d.get('PowerOnHours')} h")
        reli += [f"Read errors {int(rd)}",f"Write errors {int(wr)}"]
        add(rows,"Storage",f"Disk {i} reliability"," | ".join(reli),note="Confirm SMART with CrystalDiskInfo")
    summary["storage_status"]=overall


def scan_devices(rows,summary):
    data,err=ps("Get-PnpDevice -PresentOnly | Select Class,FriendlyName,Status",55)
    ds=data if isinstance(data,list) else [data] if data else []
    blob='\n'.join(f"{x.get('Class','')} {x.get('FriendlyName','')}" for x in ds).lower()
    specs={
      "Wi-Fi":(["wireless","wi-fi","802.11"],4,False),"Bluetooth":(["bluetooth"],3,False),
      "Camera":(["camera","webcam","integrated cam"],3,False),"Microphone":(["microphone","mic array","audio input"],2,False),
      "Audio":(["speaker","audio","sound"],2,False),"Fingerprint":(["fingerprint","biometric"],0,True),
      "Touchscreen":(["touch screen","touchscreen"],0,True),"Sensors":(["sensor","accelerometer","orientation"],0,True)}
    found={}
    for name,(keys,w,opt) in specs.items():
        ok=any(k in blob for k in keys); found[name]=ok
        add(rows,"Devices",name,"Detected" if ok else "Not detected","PASS" if ok else "INFO" if opt else "WARN","Optional on some models" if opt else "Windows PnP detection",w,opt)
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
    return rows,summary


def factor(s): return {"PASS":1.0,"WARN":.55,"FAIL":0.0}.get(s)

def score(rows):
    vals=[(r["weight"],factor(r["status"])) for r in rows if r.get("weight",0)>0 and factor(r["status"]) is not None]
    d=sum(w for w,_ in vals); return round(sum(w*f for w,f in vals)/d*100) if d else 0

def completion(rows):
    a=[r for r in rows if r.get("weight",0)>0]; total=sum(r["weight"] for r in a)
    done=sum(r["weight"] for r in a if r["status"] in {"PASS","WARN","FAIL"}); return round(done/total*100) if total else 0

def recommendation(rows):
    s=score(rows); c=completion(rows)
    if c<70: return "INCOMPLETE","Complete the remaining high-value tests before buying."
    critical=any(r["status"]=="FAIL" and (r["category"]=="Storage" or "Display" in r["item"] or "BIOS Password" in r["item"]) for r in rows)
    if critical: return "REJECT","A critical storage/display/BIOS check failed."
    if s>=85: return "BUY","Strong overall condition. Buy if price and warranty are fair."
    if s>=68: return "NEGOTIATE","Usable, but warnings/wear justify rechecking and negotiating."
    return "REJECT","Too many health concerns for a used-laptop purchase."
