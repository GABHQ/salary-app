from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
from datetime import datetime, timedelta
from dateutil import parser
import pytz

app = FastAPI()
TIMEZONE = pytz.timezone('Asia/Jerusalem')

class ShiftRequest(BaseModel):
    start_time: str
    end_time: str
    base_rate: float
    break_mins: int = 0
    extra_pay: float = 0
    overtime_125_after: float = 8.5
    overtime_150_after: float = 10.5
    holiday_rate: float = 1.5

def get_holidays(year):
    url = f"https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&min=on&mod=on&nx=on&year={year}&month=all&ss=on&mf=on&c=on"
    try:
        r = requests.get(url, timeout=5)
        return r.json().get('items', [])
    except: return []

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    return """
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Smart Salary Pro</title>
        <link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;700;900&display=swap" rel="stylesheet">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            :root { 
                --bg: #f8fafc; --card: rgba(255, 255, 255, 0.8); --text: #0f172a; 
                --accent: #06b6d4; --nav-bg: rgba(255, 255, 255, 0.7); 
            }
            body.dark { 
                --bg: #020617; --card: rgba(30, 41, 59, 0.7); --text: #f1f5f9; 
                --accent: #22d3ee; --nav-bg: rgba(15, 23, 42, 0.8); 
            }
            
            body { 
                font-family: 'Heebo', sans-serif;
                background-color: var(--bg); 
                color: var(--text); 
                transition: background 0.4s ease;
                margin: 0; padding-bottom: 90px;
                overflow-x: hidden;
            }

            /* Glassmorphism Effect */
            .glass {
                backdrop-filter: blur(16px) saturate(180%);
                -webkit-backdrop-filter: blur(16px) saturate(180%);
                background-color: var(--nav-bg);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }

            .card { 
                background-color: var(--card); 
                backdrop-filter: blur(8px);
                border-radius: 28px; 
                border: 1px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
                transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease;
            }
            .card:active { transform: scale(0.96); }

            .modal { 
                display: none; position: fixed; inset: 0; 
                background: rgba(0, 0, 0, 0.4); 
                backdrop-filter: blur(4px);
                align-items: flex-end; z-index: 500; 
            }
            .modal-content { 
                background: var(--bg); 
                border-radius: 40px 40px 0 0; 
                padding: 32px; width: 100%; 
                box-shadow: 0 -10px 40px rgba(0,0,0,0.2);
                animation: slideUp 0.4s cubic-bezier(0, 0.55, 0.45, 1);
            }
            @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }

            .nav-item { transition: all 0.3s ease; position: relative; }
            .nav-item.active { color: var(--accent); transform: translateY(-4px); }
            .nav-item.active::after {
                content: ''; position: absolute; bottom: -8px; left: 50%; transform: translateX(-50%);
                width: 4px; height: 4px; background: var(--accent); border-radius: 50%;
            }

            input, select, textarea { 
                background: var(--card) !important; 
                border: 2px solid transparent !important;
                border-radius: 18px !important;
                padding: 14px !important;
                transition: border 0.3s ease;
            }
            input:focus { border-color: var(--accent) !important; }

            .btn-primary {
                background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
                box-shadow: 0 10px 20px -10px #06b6d4;
            }

            .fade-in { animation: fadeIn 0.5s ease-out; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        </style>
    </head>
    <body class="dark"> <header class="glass p-5 flex justify-between items-center sticky top-0 z-50">
            <h1 id="view-title" class="text-xl font-black tracking-tight">Smart Salary</h1>
            <div class="flex gap-4">
                <span class="material-icons cursor-pointer opacity-70" onclick="setTheme(document.body.classList.contains('dark') ? 'light' : 'dark')">dark_mode</span>
                <span class="material-icons cursor-pointer text-cyan-400 scale-125" onclick="openShiftModal()">add_circle</span>
            </div>
        </header>

        <main id="main-content" class="p-6 space-y-6">
            </main>

        <nav class="glass fixed bottom-0 left-0 right-0 h-20 flex justify-around items-center z-[400] rounded-t-[32px]">
            <div class="nav-item" onclick="setView('home')" id="nav-home"><span class="material-icons">grid_view</span></div>
            <div class="nav-item" onclick="setView('jobs')" id="nav-jobs"><span class="material-icons">account_balance_wallet</span></div>
            <div class="nav-item" id="nav-stats"><span class="material-icons">leaderboard</span></div>
            <div class="nav-item" onclick="openSettings()" id="nav-settings"><span class="material-icons">tune</span></div>
        </nav>

        <div id="settingsModal" class="modal" onclick="if(event.target==this)closeAll()">
            <div class="modal-content">
                <h2 class="text-2xl font-black mb-6">הגדרות</h2>
                <div id="jobs-manager-list" class="space-y-3 mb-8"></div>
                <div class="card p-6 space-y-4">
                    <p class="text-xs font-bold opacity-40 uppercase tracking-widest">הוספת עבודה חדשה</p>
                    <input id="j_name" placeholder="שם העבודה (למשל: גוסטה)">
                    <div class="grid grid-cols-2 gap-3">
                        <input id="j_rate" type="number" placeholder="שכר שעתי">
                        <select id="j_culture"><option value="jewish">יהודי ✡️</option><option value="muslim">מוסלמי ☪️</option></select>
                    </div>
                    <button onclick="saveJob()" class="btn-primary w-full text-white py-4 rounded-2xl font-bold">צור עבודה</button>
                </div>
            </div>
        </div>

        <div id="shiftModal" class="modal" onclick="if(event.target==this)closeAll()">
            <div class="modal-content">
                <h2 class="text-2xl font-black mb-6 text-cyan-500">תיעוד משמרת</h2>
                <div class="space-y-4">
                    <div id="job-selector-container">
                        <select id="s_job"></select>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="date" id="s_date">
                        <div class="flex gap-2">
                            <input type="time" id="s_start" value="18:00">
                            <input type="time" id="s_end" value="02:00">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="number" id="s_break" placeholder="הפסקה (דק')">
                        <input type="number" id="s_extra" placeholder="בונוס/טיפ">
                    </div>
                    <textarea id="s_notes" placeholder="הערות אישיות..." rows="2"></textarea>
                    <button onclick="saveShift()" class="btn-primary w-full text-white py-4 rounded-2xl font-bold">שמור משמרת</button>
                </div>
            </div>
        </div>

        <script>
            let jobs = JSON.parse(localStorage.getItem('jobs')) || [];
            let shifts = JSON.parse(localStorage.getItem('shifts')) || [];
            let currentView = localStorage.getItem('lastView') || 'home';
            let currentJobId = localStorage.getItem('lastJobId') || null;

            window.onload = () => {
                applySettings();
                renderView();
            };

            function applySettings() {
                const theme = localStorage.getItem('theme') || 'dark';
                document.body.className = theme;
            }

            function setTheme(t) {
                document.body.className = t;
                localStorage.setItem('theme', t);
            }

            function setView(view, jobId = null) {
                currentView = view;
                currentJobId = jobId;
                localStorage.setItem('lastView', view);
                if(jobId) localStorage.setItem('lastJobId', jobId);
                renderView();
            }

            function renderView() {
                const main = document.getElementById('main-content');
                main.innerHTML = '';
                main.classList.add('fade-in');
                setTimeout(() => main.classList.remove('fade-in'), 500);

                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                
                if (currentView === 'home') {
                    document.getElementById('nav-home').classList.add('active');
                    document.getElementById('view-title').innerText = 'הארנק שלי';
                    renderHome(main);
                } else if (currentView === 'jobs') {
                    document.getElementById('nav-jobs').classList.add('active');
                    document.getElementById('view-title').innerText = 'מקומות עבודה';
                    renderJobsList(main);
                } else if (currentView === 'job') {
                    document.getElementById('nav-jobs').classList.add('active');
                    const job = jobs.find(j => j.id == currentJobId);
                    document.getElementById('view-title').innerText = job.name;
                    renderJobDetails(main, job);
                }
            }

            function renderHome(container) {
                const totalGross = shifts.reduce((acc, s) => acc + s.data.total_pay, 0);
                container.innerHTML = `
                    <div class="card p-10 text-center relative overflow-hidden">
                        <div class="absolute top-0 right-0 w-32 h-32 bg-cyan-500/10 rounded-full -mr-16 -mt-16"></div>
                        <p class="text-[11px] font-black uppercase opacity-40 tracking-widest mb-2">סה"כ הכנסות (ברוטו)</p>
                        <p class="text-5xl font-black text-cyan-500">₪${totalGross.toLocaleString()}</p>
                    </div>
                    <div class="flex justify-between items-center px-2">
                        <h3 class="font-bold text-lg">פעולות אחרונות</h3>
                        <span class="text-xs text-cyan-500 font-bold">הכל</span>
                    </div>
                    <div class="space-y-4">
                        ${shifts.sort((a,b) => new Date(b.start) - new Date(a.start)).slice(0,8).map(s => `
                            <div class="card p-5 flex justify-between items-center" onclick="alert('${s.notes || "אין הערות"}')">
                                <div class="flex items-center gap-4">
                                    <div class="w-12 h-12 bg-cyan-500/20 rounded-2xl flex items-center justify-center text-cyan-500">
                                        <span class="material-icons">payments</span>
                                    </div>
                                    <div><p class="font-black text-sm uppercase tracking-tighter">${s.jobName}</p><p class="text-[10px] opacity-40">${s.start.split('T')[0]}</p></div>
                                </div>
                                <div class="font-black text-lg">₪${s.data.total_pay}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            function renderJobsList(container) {
                container.innerHTML = jobs.map(j => `
                    <div class="card p-6 flex justify-between items-center" onclick="setView('job', ${j.id})">
                        <div class="flex items-center gap-4">
                            <div class="w-14 h-14 bg-gray-500/10 rounded-3xl flex items-center justify-center text-2xl font-black text-cyan-500">
                                ${j.name.charAt(0)}
                            </div>
                            <div>
                                <p class="font-black text-xl">${j.name}</p>
                                <p class="text-xs opacity-40">${j.rate}₪ לשעה • ${j.type === 'monthly' ? 'גלובלי' : 'שעתי'}</p>
                            </div>
                        </div>
                        <span class="material-icons opacity-20">arrow_back_ios</span>
                    </div>
                `).join('') + (jobs.length === 0 ? '<p class="text-center opacity-40 py-20">אין עבודות? הוסף אחת בהגדרות</p>' : '');
            }

            function renderJobDetails(container, job) {
                const jobShifts = shifts.filter(s => s.jobId == job.id).sort((a,b) => new Date(b.start) - new Date(a.start));
                container.innerHTML = `
                    <div class="space-y-4">
                        ${jobShifts.map(s => `
                            <div class="card p-5 flex justify-between items-center">
                                <div><p class="text-[10px] opacity-40 font-bold">${s.start.split('T')[0]}</p><p class="font-black">${s.start.split('T')[1]} - ${s.end.split('T')[1]}</p></div>
                                <div class="text-right">
                                    <p class="text-xl font-black text-cyan-500">₪${s.data.total_pay}</p>
                                    <span class="text-[9px] font-bold text-red-400" onclick="deleteShift(${s.id})">מחיקה</span>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    <div class="glass fixed bottom-20 left-0 right-0 p-6 flex justify-around items-center border-t border-white/5">
                        <div class="text-center"><p class="text-[10px] font-bold opacity-40 uppercase">שעות</p><p class="text-xl font-black">${jobShifts.reduce((acc,s)=>acc+s.data.hours,0).toFixed(1)}</p></div>
                        <div class="text-center"><p class="text-[10px] font-bold opacity-40 uppercase">ברוטו</p><p class="text-xl font-black text-cyan-500">₪${jobShifts.reduce((acc,s)=>acc+s.data.total_pay,0).toLocaleString()}</p></div>
                    </div>
                `;
            }

            function openShiftModal() {
                const sel = document.getElementById('job-selector-container');
                const select = document.getElementById('s_job');
                select.innerHTML = jobs.map(j => `<option value="${j.id}">${j.name}</option>`).join('');
                if (currentView === 'job') { select.value = currentJobId; sel.classList.add('hidden'); }
                else { sel.classList.remove('hidden'); }
                document.getElementById('shiftModal').style.display = 'flex';
            }

            function saveJob() {
                const name = document.getElementById('j_name').value;
                const rate = document.getElementById('j_rate').value;
                if(!name || !rate) return;
                jobs.push({ id: Date.now(), name, rate: parseFloat(rate), type: 'hourly' });
                localStorage.setItem('jobs', JSON.stringify(jobs));
                closeAll(); renderView();
            }

            async function saveShift() {
                const jobId = document.getElementById('s_job').value;
                const job = jobs.find(j => j.id == jobId);
                const start = document.getElementById('s_date').value + 'T' + document.getElementById('s_start').value;
                const end = document.getElementById('s_date').value + 'T' + document.getElementById('s_end').value;

                const res = await fetch('/api/calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        start_time: start, end_time: end, base_rate: job.rate,
                        break_mins: parseInt(document.getElementById('s_break').value || 0),
                        extra_pay: parseFloat(document.getElementById('s_extra').value || 0)
                    })
                });
                const data = await res.json();
                shifts.push({ id: Date.now(), jobId, jobName: job.name, start, end, data, notes: document.getElementById('s_notes').value });
                localStorage.setItem('shifts', JSON.stringify(shifts));
                closeAll(); renderView();
            }

            function closeAll() { document.querySelectorAll('.modal').forEach(m => m.style.display='none'); }
            function openSettings() { renderJobsManager(); document.getElementById('settingsModal').style.display = 'flex'; }
            function renderJobsManager() {
                document.getElementById('jobs-manager-list').innerHTML = jobs.map(j => `<div class="card p-4 flex justify-between mb-2"><span class="font-bold">${j.name}</span><span class="material-icons text-red-400 text-sm" onclick="deleteJob(${j.id})">delete</span></div>`).join('');
            }
            function deleteJob(id) { jobs = jobs.filter(j=>j.id!=id); localStorage.setItem('jobs', JSON.stringify(jobs)); renderJobsManager(); renderView(); }
            function deleteShift(id) { if(confirm('למחוק?')) { shifts = shifts.filter(s=>s.id!=id); localStorage.setItem('shifts', JSON.stringify(shifts)); renderView(); } }
        </script>
    </body>
    </html>
    """

@app.post("/api/calculate")
async def calculate(shift: ShiftRequest):
    # (Same Python logic as before - calculating overtime and holidays)
    start = parser.isoparse(shift.start_time).astimezone(TIMEZONE)
    end = parser.isoparse(shift.end_time).astimezone(TIMEZONE)
    if end < start: end += timedelta(days=1)
    holidays = get_holidays(start.year)
    total_pay = 0
    curr = start
    step = timedelta(minutes=15)
    duration_hours = (end - start).total_seconds() / 3600
    actual_work_hours = duration_hours - (shift.break_mins / 60)
    
    while curr < end:
        mult = 1.0
        if (curr.weekday() == 4 and curr.hour >= 18) or (curr.weekday() == 5 and curr.hour < 20):
            mult = 1.5
        for h in holidays:
            if h.get('date') == curr.strftime('%Y-%m-%d'):
                mult = shift.holiday_rate
                break
        
        elapsed = (curr - start).total_seconds() / 3600
        if elapsed >= shift.overtime_150_after: mult = max(mult, 1.5)
        elif elapsed >= shift.overtime_125_after: mult = max(mult, 1.25)
            
        total_pay += (shift.base_rate * mult) * (15/60)
        curr += step

    final_pay = round(total_pay - ((shift.break_mins / 60) * shift.base_rate) + shift.extra_pay, 2)
    return {"total_pay": max(0, final_pay), "hours": actual_work_hours}
