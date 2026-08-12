import os, subprocess, threading, time, webbrowser, tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from datetime import datetime
from core import VERSION, add, auto_scan, score, completion, recommendation
from reporting import export_report

C={"bg":"#0b1220","panel":"#111b2e","panel2":"#16233b","text":"#edf4ff","muted":"#9fb0c7","accent":"#4f8cff","pass":"#26c281","warn":"#f5b942","fail":"#ff5d73","info":"#60a5fa","manual":"#a78bfa","border":"#253651"}
T={
"en":{"sub":"Professional Used-Laptop Inspection Assistant","scan":"Run Auto Scan","export":"Export Report","lang":"বাংলা","auto":"Auto Scan","manual":"Manual Tests","final":"Final Checks","score":"Overall Health","done":"Test Completion","battery":"Battery Grade","storage":"Storage Health","rec":"Recommendation","not":"Not scanned","scanning":"Scanning hardware...","complete":"Auto scan completed","display":"Display Test","keyboard":"Keyboard Test","touch":"Touch / 2-in-1 Test","camera":"Webcam Test","mic":"Microphone Test","speaker":"Speaker Test","ports":"Ports & Charger Test","body":"Body & Hinge Test","bios":"BIOS Password Check","diag":"Built-in Hardware Diagnostics","memory":"Windows Memory Diagnostic","crystal":"Open CrystalDiskInfo","hwinfo":"Open HWiNFO","finish":"Finish & Mark Result"},
"bn":{"sub":"প্রফেশনাল ইউজড-ল্যাপটপ ইন্সপেকশন অ্যাসিস্ট্যান্ট","scan":"অটো স্ক্যান চালান","export":"রিপোর্ট এক্সপোর্ট","lang":"English","auto":"অটো স্ক্যান","manual":"ম্যানুয়াল টেস্ট","final":"ফাইনাল চেক","score":"সামগ্রিক স্বাস্থ্য","done":"টেস্ট সম্পন্ন","battery":"ব্যাটারি গ্রেড","storage":"স্টোরেজ স্বাস্থ্য","rec":"সুপারিশ","not":"এখনও স্ক্যান হয়নি","scanning":"হার্ডওয়্যার স্ক্যান হচ্ছে...","complete":"অটো স্ক্যান সম্পন্ন","display":"ডিসপ্লে টেস্ট","keyboard":"কিবোর্ড টেস্ট","touch":"টাচ / 2-in-1 টেস্ট","camera":"ওয়েবক্যাম টেস্ট","mic":"মাইক্রোফোন টেস্ট","speaker":"স্পিকার টেস্ট","ports":"পোর্ট ও চার্জার টেস্ট","body":"বডি ও হিঞ্জ টেস্ট","bios":"BIOS পাসওয়ার্ড চেক","diag":"বিল্ট-ইন হার্ডওয়্যার ডায়াগনস্টিকস","memory":"Windows Memory Diagnostic","crystal":"CrystalDiskInfo খুলুন","hwinfo":"HWiNFO খুলুন","finish":"শেষ করুন ও রেজাল্ট দিন"}}

MANUAL=[("Display","Display Test",10,False),("Input","Keyboard Test",5,False),("Devices","Touch / 2-in-1 Test",0,True),("Devices","Webcam Test",4,False),("Devices","Microphone Test",3,False),("Devices","Speaker Test",3,False),("Ports","Ports & Charger Test",5,False),("Physical","Body & Hinge Test",5,False),("BIOS","BIOS Password Check",6,False),("Diagnostics","Built-in Hardware Diagnostics",6,False)]

class Card(tk.Frame):
    def __init__(self,p,title):
        super().__init__(p,bg=C['panel'],highlightthickness=1,highlightbackground=C['border']); self.t=tk.Label(self,text=title,bg=C['panel'],fg=C['muted'],font=('Segoe UI',10)); self.t.pack(anchor='w',padx=14,pady=(12,2)); self.v=tk.Label(self,text='—',bg=C['panel'],fg=C['text'],font=('Segoe UI',20,'bold')); self.v.pack(anchor='w',padx=14,pady=(0,12))
    def set(self,title,val,color=None): self.t.config(text=title); self.v.config(text=val,fg=color or C['text'])

class LaptopCheckApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.lang='en'; self.rows=[]; self.summary={}; self.scanned=False; self.labels={}; self._window(); self._style(); self._ui(); self._seed(); self.refresh()
    def x(self,k): return T[self.lang][k]
    def _window(self): self.title(f'Laptop Check Pro v{VERSION}'); self.geometry('1180x780'); self.minsize(1000,670); self.configure(bg=C['bg'])
    def _style(self):
        s=ttk.Style(self); s.theme_use('clam'); s.configure('TNotebook',background=C['bg'],borderwidth=0); s.configure('TNotebook.Tab',background=C['panel'],foreground=C['muted'],padding=(14,9),font=('Segoe UI',10,'bold')); s.map('TNotebook.Tab',background=[('selected',C['panel2'])],foreground=[('selected',C['text'])]); s.configure('Treeview',background=C['panel'],fieldbackground=C['panel'],foreground=C['text'],rowheight=28,borderwidth=0); s.configure('Treeview.Heading',background=C['panel2'],foreground=C['text'],relief='flat'); s.configure('Horizontal.TProgressbar',troughcolor=C['panel2'],background=C['accent'])
    def btn(self,p,text,cmd,primary=False): return tk.Button(p,text=text,command=cmd,bg=C['accent'] if primary else C['panel2'],fg='white',activebackground='#6ea8ff' if primary else '#213451',activeforeground='white',relief='flat',bd=0,padx=14,pady=8,cursor='hand2',font=('Segoe UI',10,'bold'))
    def _ui(self):
        h=tk.Frame(self,bg=C['bg']); h.pack(fill='x',padx=18,pady=(16,10)); l=tk.Frame(h,bg=C['bg']); l.pack(side='left',fill='x',expand=True); tk.Label(l,text='Laptop Check Pro',bg=C['bg'],fg=C['text'],font=('Segoe UI',22,'bold')).pack(anchor='w'); self.sub=tk.Label(l,text=self.x('sub'),bg=C['bg'],fg=C['muted']); self.sub.pack(anchor='w'); a=tk.Frame(h,bg=C['bg']); a.pack(side='right'); self.langb=self.btn(a,self.x('lang'),self.toggle); self.langb.pack(side='right',padx=(8,0)); self.exp=self.btn(a,self.x('export'),self.export); self.exp.pack(side='right',padx=(8,0)); self.scanb=self.btn(a,self.x('scan'),self.scan,True); self.scanb.pack(side='right')
        cf=tk.Frame(self,bg=C['bg']); cf.pack(fill='x',padx=18,pady=(0,12)); [cf.grid_columnconfigure(i,weight=1,uniform='c') for i in range(5)]; self.cards=[Card(cf,self.x(k)) for k in ['score','done','battery','storage','rec']]; [c.grid(row=0,column=i,sticky='nsew',padx=(0 if i==0 else 7,0 if i==4 else 7)) for i,c in enumerate(self.cards)]
        self.prog=ttk.Progressbar(self,mode='indeterminate'); self.prog.pack(fill='x',padx=18); self.status=tk.Label(self,text=self.x('not'),bg=C['bg'],fg=C['muted']); self.status.pack(anchor='w',padx=18,pady=(4,8)); self.nb=ttk.Notebook(self); self.nb.pack(fill='both',expand=True,padx=18,pady=(0,18)); self.ta=tk.Frame(self.nb,bg=C['panel']); self.tm=tk.Frame(self.nb,bg=C['panel']); self.tf=tk.Frame(self.nb,bg=C['panel']); self.nb.add(self.ta,text=self.x('auto')); self.nb.add(self.tm,text=self.x('manual')); self.nb.add(self.tf,text=self.x('final')); self._auto_tab(); self._manual_tab(); self._final_tab()
    def _auto_tab(self):
        f=tk.Frame(self.ta,bg=C['panel']); f.pack(fill='both',expand=True,padx=8,pady=8); cols=('category','item','value','status','note'); self.tree=ttk.Treeview(f,columns=cols,show='headings'); widths=(100,180,315,90,335)
        for c,w in zip(cols,widths): self.tree.heading(c,text=c.title()); self.tree.column(c,width=w,anchor='w')
        sc=ttk.Scrollbar(f,orient='vertical',command=self.tree.yview); self.tree.configure(yscrollcommand=sc.set); self.tree.pack(side='left',fill='both',expand=True); sc.pack(side='right',fill='y'); [self.tree.tag_configure(k,foreground=C[k.lower()]) for k in ['PASS','WARN','FAIL','INFO','MANUAL']]
    def _manual_tab(self):
        w=tk.Frame(self.tm,bg=C['panel']); w.pack(fill='both',expand=True,padx=10,pady=10); tests=[('display',self.display),('keyboard',self.keyboard),('touch',self.touch),('camera',self.camera),('mic',self.mic),('speaker',self.speaker),('ports',lambda:self.mark('Ports & Charger Test')),('body',lambda:self.mark('Body & Hinge Test')),('bios',self.bios),('diag',self.diag)]
        for i,(k,cmd) in enumerate(tests):
            r,c=divmod(i,2); w.grid_columnconfigure(c,weight=1); box=tk.Frame(w,bg=C['panel2'],highlightthickness=1,highlightbackground=C['border']); box.grid(row=r,column=c,sticky='nsew',padx=7,pady=7); lab=tk.Label(box,text=self.x(k),bg=C['panel2'],fg=C['text'],font=('Segoe UI',11,'bold')); lab.pack(anchor='w',padx=14,pady=(12,8)); self.labels[k]=lab; self.btn(box,'Run / Start',cmd).pack(anchor='w',padx=14,pady=(0,12))
        tools=tk.Frame(w,bg=C['panel']); tools.grid(row=5,column=0,columnspan=2,sticky='ew',padx=7,pady=8); self.memb=self.btn(tools,self.x('memory'),self.mem); self.memb.pack(side='left',padx=(0,8)); self.crys=self.btn(tools,self.x('crystal'),lambda:webbrowser.open('https://crystalmark.info/en/software/crystaldiskinfo/')); self.crys.pack(side='left',padx=(0,8)); self.hwi=self.btn(tools,self.x('hwinfo'),lambda:webbrowser.open('https://www.hwinfo.com/download/')); self.hwi.pack(side='left')
    def _final_tab(self):
        self.ft=tk.Text(self.tf,wrap='word',bg=C['panel2'],fg=C['text'],insertbackground='white',relief='flat',padx=18,pady=18,font=('Segoe UI',10)); self.ft.pack(fill='both',expand=True,padx=16,pady=16); self._final_text()
    def _final_text(self):
        en="""FINAL BUYING CHECKLIST\n\n• Prefer battery health 80%+; below 70% should reduce price or assume battery replacement.\n• Storage should report Healthy; confirm SMART/health with CrystalDiskInfo.\n• Display: no dead pixel, white spot, line, flicker or uneven backlight.\n• Test every keyboard key, touchpad, camera, microphone and speaker.\n• Test USB-A, USB-C/Thunderbolt, HDMI, audio jack and charger.\n• BIOS Admin/System password must NOT be set.\n• Run the manufacturer's built-in hardware diagnostics; Dell: F12 → Diagnostics/ePSA.\n• 2-in-1: Laptop → Tent → Stand → Tablet, touch and auto-rotation.\n• Inspect body, hinge, screws, bezel, charging port and repair/liquid signs.\n• Put exact model, CPU/RAM/SSD, Service Tag and warranty on the invoice."""; bn="""ফাইনাল কেনার চেকলিস্ট\n\n• Battery health 80%+ ভালো; 70%-এর নিচে হলে দাম কমান বা battery replacement ধরুন।\n• Storage Healthy হওয়া উচিত; CrystalDiskInfo দিয়ে SMART/health confirm করুন।\n• Display-এ dead pixel, white spot, line, flicker বা uneven backlight থাকবে না।\n• সব keyboard key, touchpad, camera, microphone ও speaker test করুন।\n• USB-A, USB-C/Thunderbolt, HDMI, audio jack ও charger test করুন।\n• BIOS Admin/System password set থাকা যাবে না।\n• Manufacturer-এর built-in diagnostics চালান; Dell: F12 → Diagnostics/ePSA।\n• 2-in-1: Laptop → Tent → Stand → Tablet, touch ও auto-rotation test করুন।\n• Body, hinge, screw, bezel, charging port এবং repair/liquid signs inspect করুন।\n• Invoice-এ exact model, CPU/RAM/SSD, Service Tag ও warranty লিখিয়ে নিন।"""; self.ft.config(state='normal'); self.ft.delete('1.0','end'); self.ft.insert('1.0',bn if self.lang=='bn' else en); self.ft.config(state='disabled')
    def _seed(self):
        for cat,item,w,opt in MANUAL:
            if not any(r['item']==item and r['category']==cat for r in self.rows): add(self.rows,cat,item,'Pending manual test','MANUAL','Complete before purchase',w,opt)
    def _manual(self,item): return next((r for r in self.rows if r['item']==item and r['status'] in {'MANUAL','PASS','FAIL','WARN'} and any(item==x[1] for x in MANUAL)),None)
    def mark(self,item,note=''):
        ans=messagebox.askyesnocancel('Test Result',f"{item}\n\nDid this test pass?\nYes = PASS | No = FAIL | Cancel = Pending"+(f"\n\n{note}" if note else ''))
        if ans is None:return
        r=self._manual(item); r.update(status='PASS' if ans else 'FAIL',value='Passed' if ans else 'Failed',note=note or r['note']); self.refresh()
    def scan(self):
        keep=[dict(r) for r in self.rows if any(r['item']==x[1] for x in MANUAL)]; self.prog.start(10); self.status.config(text=self.x('scanning'),fg=C['accent']); self.scanb.config(state='disabled')
        def work():
            a,s=auto_scan(); self.after(0,lambda:self._done(a,s,keep))
        threading.Thread(target=work,daemon=True).start()
    def _done(self,a,s,keep):
        self.prog.stop(); self.scanb.config(state='normal'); self.rows=a; self.summary=s; self.scanned=True
        for r in keep:
            if not any(x['item']==r['item'] and x['category']==r['category'] for x in self.rows): self.rows.append(r)
        self._seed(); self.status.config(text=self.x('complete'),fg=C['pass']); self.refresh()
    def refresh(self):
        [self.tree.delete(x) for x in self.tree.get_children()]
        for r in self.rows:self.tree.insert('', 'end',values=(r['category'],r['item'],r['value'],r['status'],r['note']),tags=(r['status'],))
        s=score(self.rows) if self.scanned else 0; d=completion(self.rows) if self.scanned else 0; rec,_=recommendation(self.rows) if self.scanned else ('INCOMPLETE',''); bh=self.summary.get('battery_health') if self.summary else None; bg=self.summary.get('battery_grade','—') if self.summary else '—'; st=self.summary.get('storage_status','INFO') if self.summary else 'INFO'; col=lambda st:C['pass'] if st=='PASS' else C['warn'] if st=='WARN' else C['fail'] if st=='FAIL' else C['manual']
        self.cards[0].set(self.x('score'),f'{s}/100' if self.scanned else '—',C['pass'] if s>=85 else C['warn'] if s>=68 else C['fail']); self.cards[1].set(self.x('done'),f'{d}%' if self.scanned else '—',C['accent']); self.cards[2].set(self.x('battery'),f'{bg} · {bh}%' if bh is not None else bg,C['pass'] if bg in {'A','B'} else C['warn'] if bg in {'C','D'} else C['fail'] if bg=='F' else C['muted']); self.cards[3].set(self.x('storage'),st,col(st)); self.cards[4].set(self.x('rec'),rec,C['pass'] if rec=='BUY' else C['warn'] if rec=='NEGOTIATE' else C['fail'] if rec=='REJECT' else C['manual'])
    def toggle(self):
        self.lang='bn' if self.lang=='en' else 'en'; self.sub.config(text=self.x('sub')); self.scanb.config(text=self.x('scan')); self.exp.config(text=self.x('export')); self.langb.config(text=self.x('lang')); self.nb.tab(self.ta,text=self.x('auto')); self.nb.tab(self.tm,text=self.x('manual')); self.nb.tab(self.tf,text=self.x('final')); [lab.config(text=self.x(k)) for k,lab in self.labels.items()]; self.memb.config(text=self.x('memory')); self.crys.config(text=self.x('crystal')); self.hwi.config(text=self.x('hwinfo')); self.status.config(text=self.x('complete') if self.scanned else self.x('not')); self._final_text(); self.refresh()
    def display(self):
        w=tk.Toplevel(self); w.attributes('-fullscreen',True); colors=['black','white','red','green','blue','gray']; st={'i':0}; w.configure(bg=colors[0]); lab=tk.Label(w,text='Click / Space: next   |   Esc: finish',bg=colors[0],fg='orange',font=('Segoe UI',14,'bold')); lab.pack(side='bottom',pady=24)
        def nxt(e=None):
            st['i']+=1
            if st['i']>=len(colors):w.destroy(); self.mark('Display Test','Check dead pixels, white spots, lines, flicker and uneven backlight.'); return
            w.configure(bg=colors[st['i']]); lab.config(bg=colors[st['i']])
        w.bind('<space>',nxt); w.bind('<Button-1>',nxt); w.bind('<Escape>',lambda e:(w.destroy(),self.mark('Display Test')))
    def keyboard(self):
        w=tk.Toplevel(self); w.title('Keyboard Test'); w.geometry('820x520'); w.configure(bg=C['bg']); tk.Label(w,text='Press every key: A-Z, 0-9, Enter, Shift, Ctrl, arrows and F-keys.',bg=C['bg'],fg=C['text'],font=('Segoe UI',11,'bold')).pack(anchor='w',padx=16,pady=16); box=tk.Text(w,bg=C['panel'],fg=C['text'],insertbackground='white',relief='flat',font=('Consolas',12)); box.pack(fill='both',expand=True,padx=16,pady=8); self.btn(w,self.x('finish'),lambda:(w.destroy(),self.mark('Keyboard Test'))).pack(pady=14); box.focus_set()
    def touch(self):
        w=tk.Toplevel(self); w.title('Touch / 2-in-1 Test'); w.geometry('860x600'); tk.Label(w,text='Draw across the full panel. Also test Laptop → Tent → Stand → Tablet and auto-rotation.',font=('Segoe UI',10,'bold')).pack(anchor='w',padx=14,pady=12); c=tk.Canvas(w,bg='white'); c.pack(fill='both',expand=True,padx=14); last={'x':None,'y':None}; c.bind('<Button-1>',lambda e:last.update(x=e.x,y=e.y)); c.bind('<B1-Motion>',lambda e:(c.create_line(last['x'],last['y'],e.x,e.y,width=4,fill='#1565c0') if last['x'] is not None else None,last.update(x=e.x,y=e.y))); self.btn(w,self.x('finish'),lambda:(w.destroy(),self.mark('Touch / 2-in-1 Test'))).pack(pady=12)
    def camera(self):
        if os.name=='nt': subprocess.Popen(['cmd','/c','start','','microsoft.windows.camera:'])
        messagebox.showinfo('Webcam Test','Check image, focus, flicker and privacy shutter.'); self.mark('Webcam Test')
    def mic(self):
        if os.name=='nt': subprocess.Popen(['cmd','/c','start','','ms-settings:sound'])
        messagebox.showinfo('Microphone Test','Speak and confirm the Windows input level meter reacts cleanly.'); self.mark('Microphone Test')
    def speaker(self):
        try:
            import winsound; winsound.Beep(660,350); time.sleep(.1); winsound.Beep(880,350)
        except: pass
        self.mark('Speaker Test','Confirm clear sound without crackling/distortion.')
    def bios(self):
        m=(self.summary.get('manufacturer') or '').lower(); hint='Open BIOS and confirm Admin/System/Supervisor password is NOT set.'; hint=('Dell: restart → F2. '+hint) if 'dell' in m else ('HP: restart → Esc/F10. '+hint) if 'hp' in m else ('Lenovo: restart → F1/F2. '+hint) if 'lenovo' in m else hint; messagebox.showinfo('BIOS Password Check',hint); self.mark('BIOS Password Check',hint)
    def diag(self):
        m=(self.summary.get('manufacturer') or '').lower(); hint='Run the manufacturer built-in hardware diagnostics and require all tests to pass.'; hint=('Dell: restart → F12 → Diagnostics/ePSA. '+hint) if 'dell' in m else hint; messagebox.showinfo('Hardware Diagnostics',hint); self.mark('Built-in Hardware Diagnostics',hint)
    def mem(self):
        try: subprocess.Popen(['mdsched.exe'])
        except Exception as e: messagebox.showerror('Error',str(e))
    def export(self):
        if not self.scanned and not messagebox.askyesno('Laptop Check Pro','Run Auto Scan first for a meaningful report. Export anyway?'): return
        p=filedialog.asksaveasfilename(defaultextension='.html',filetypes=[('HTML Report','*.html')],initialfile=f"Laptop_Check_Pro_{datetime.now():%Y%m%d_%H%M}.html")
        if p: export_report(self.rows,self.summary,p); messagebox.showinfo('Laptop Check Pro',f"HTML + JSON report saved.\n{p}\n{Path(p).with_suffix('.json')}")
