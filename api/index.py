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
        <title>Smart Salary Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;700;900&display=swap" rel="stylesheet">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            :root { 
                --bg: #ffffff; --card: #f8fafc; --text: #0f172a; 
                --accent: #06b6d4; --glass: rgba(255, 255, 255, 0.8); 
            }
            body.dark { 
                --bg: #020617; --card: #1e293b; --text: #f1f5f9; 
                --accent: #22d3ee; --glass: rgba(15, 23, 42, 0.8); 
            }
            body { 
                font-family: 'Heebo', sans-serif; background-color: var(--bg); color: var(--text); 
                transition: 0.3s; margin: 0; padding-bottom: 90px; 
            }
            .glass { backdrop-filter: blur(12px); background: var(--glass); }
            .card { background: var(--card); border-radius: 24px; border: 1px solid rgba(0,0,0,0.05); color: var(--text); }
            .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); align-items: flex-end; z-index: 500; }
            .modal-content { background: var(--bg); border-radius: 32px 32px 0 0; padding: 28px; width: 100%; color: var(--text); }
            .nav-item { opacity: 0.4; transition: 0.3s; color: var(--text); text-align: center; }
            .nav-item.active { opacity: 1; color: var(--accent); }
            input, select, textarea { background: var(--card) !important; color: var(--text) !important; border: 1px solid rgba(0,0,0,0.1) !important; width: 100%; padding: 12px; border-radius: 12px; }
        </style>
    </head>
    <body>

        <header class="glass p-5 flex justify-between items-center sticky top-0 z-50">
            <h1 id="view-title" class="text-xl font-black">הארנק שלי</h1>
            <span class="material-icons text-cyan-400 scale-125 cursor-pointer" onclick="openShiftModal()">add_circle</span>
        </header>

        <main id="main-content" class="p-6 space-y-6">
            </main>

        <nav class="glass fixed bottom-0 left-0 right-0 h-20 flex justify-around items-center z-[400] rounded-t-[32px]">
            <div class="nav-item" onclick="setView('home')" id="nav-home"><span class="material-icons">grid_view</span><p class="text-[10px] font-bold">בית</p></div>
            <div class="nav-item" onclick="setView('jobs')" id="nav-jobs"><span class="material-icons">account_balance_wallet</span><p class="text-[10px] font-bold">עבודות</p></div>
            <div class="nav-item" onclick="setView('stats')" id="nav-stats"><span class="material-icons">leaderboard</span><p class="text-[10px] font-bold">השוואה</p></div>
            <div class="nav-item" onclick="openSettings()" id="nav-settings"><span class="material-icons">tune</span><p class="text-[10px] font-bold">הגדרות</p></div>
        </nav>

        <div id="settingsModal" class="modal" onclick="if(event.target==this)closeAll()">
            <div class="modal-content">
                <h2 class="text-xl font-black mb-6">הגדרות</h2>
                <div class="space-y-4">
                    <div class="card p-5">
                        <p class="text-[10px] font-bold opacity-50 mb-1">יעד הכנסה חודשי (₪)</p>
                        <input id="goal_amount" type="number" placeholder="למשל: 8000" onchange="saveGoal()">
                    </div>
                    <div id="jobs-manager-list" class="space-y-2"></div>
                    <div class="card p-5 space-y-3">
                        <p class="text-xs font-bold opacity-40">הוספת עבודה</p>
                        <input id="j_name" placeholder="שם העבודה">
                        <input id="j_rate" type="number" placeholder="שכר שעתי בסיסי">
                        <button onclick="saveJob()" class="w-full bg-cyan-600 text-white py-4 rounded-2xl font-bold">שמור עבודה</button>
                    </div>
                    <select onchange="updateTheme(this.value)" class="p-4 rounded-xl">
                        <option value="light">מצב בהיר</option>
                        <option value="dark">מצב כהה</option>
                    </select>
                </div>
                <button onclick="closeAll()" class="w-full mt-6 py-4 bg-gray-100 dark:bg-gray-800 rounded-2xl font-bold">סגור</button>
            </div>
        </div>

        <div id="shiftModal" class="modal" onclick="if(event.target==this)closeAll()">
            <div class="modal-content">
                <h2 class="text-xl font-black mb-6 text-cyan-500">תיעוד משמרת</h2>
                <div class="space-y-4">
                    <div id="job-sel-box"><select id="s_job"></select></div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="date" id="s_date">
                        <div class="flex gap-1"><input type="time" id="s_start"><input type="time" id="s_end"></div>
                    </div>
                    <input type="number" id="s_break" placeholder="הפסקה (דקות)">
                    <textarea id="s_notes" placeholder="הערות אישיות..." rows="2"></textarea>
                    <button onclick="saveShift()" class="w-full bg-cyan-600 text-white py-4 rounded-2xl font-bold shadow-lg">שמור משמרת</button>
                </div>
            </div>
        </div>

        <script>
            let jobs = JSON.parse(localStorage.getItem('jobs')) || [];
            let shifts = JSON.parse(localStorage.getItem('shifts')) || [];
            let incomeGoal = localStorage.getItem('incomeGoal') || 0;
            let currentView = localStorage.getItem('lastView') || 'home';
            let currentJobId = localStorage.getItem('lastJobId') || null;

            window.onload = () => {
                const theme = localStorage.getItem('theme') || 'dark';
                document.body.className = theme;
                document.getElementById('goal_amount').value = incomeGoal;
                renderView();
            };

            function setView(view, jobId = null) {
                currentView = view;
                currentJobId = jobId;
                localStorage.setItem('lastView', view);
                if(jobId) localStorage.setItem('lastJobId', jobId);
                renderView();
            }

            function renderView() {
                const main = document.getElementById('main-content');
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                
                if (currentView === 'home') {
                    document.getElementById('nav-home').classList.add('active');
                    document.getElementById('view-title').innerText = 'סקירה כללית';
                    renderHome(main);
                } else if (currentView === 'jobs') {
                    document.getElementById('nav-jobs').classList.add('active');
                    document.getElementById('view-title').innerText = 'העבודות שלי';
                    renderJobsList(main);
                } else if (currentView === 'stats') {
                    document.getElementById('nav-stats').classList.add('active');
                    document.getElementById('view-title').innerText = 'השוואת ביצועים';
                    renderStats(main);
                } else if (currentView === 'job') {
                    const job = jobs.find(j => j.id == currentJobId);
                    document.getElementById('view-title').innerText = job.name;
                    renderJobDetails(main, job);
                }
            }

            function renderHome(container) {
                const totalGross = shifts.reduce((acc, s) => acc + s.data.total_pay, 0);
                const progress = incomeGoal > 0 ? Math.min((totalGross / incomeGoal) * 100, 100) : 0;
                
                container.innerHTML = `
                    <div class="card p-10 text-center border-t-4 border-cyan-500 relative overflow-hidden">
                        <p class="text-[11px] font-black uppercase opacity-40 mb-2">ברוטו חודשי</p>
                        <p class="text-5xl font-black text-cyan-500">₪${totalGross.toLocaleString()}</p>
                        ${incomeGoal > 0 ? `
                            <div class="mt-6 bg-gray-200 dark:bg-gray-700 h-2 rounded-full"><div class="bg-cyan-500 h-full" style="width:${progress}%"></div></div>
                            <p class="text-[10px] mt-2 font-bold">${progress.toFixed(1)}% מהיעד</p>
                        ` : ''}
                    </div>
                    <div class="grid grid-cols-2 gap-4">
                        <div class="card p-5 text-center"><p class="text-[9px] opacity-50 uppercase">נטו משוער</p><p class="font-black text-lg">₪${(totalGross * 0.88).toLocaleString()}</p></div>
                        <div class="text-center card p-5"><p class="text-[9px] opacity-50 uppercase">שעות סה"כ</p><p class="font-black text-lg">${shifts.reduce((acc,s)=>acc+s.data.hours,0).toFixed(1)}</p></div>
                    </div>
                    <div class="space-y-3">
                        <p class="text-xs font-bold opacity-40 px-2 uppercase">פעולות אחרונות</p>
                        ${shifts.sort((a,b) => new Date(b.start) - new Date(a.start)).slice(0,5).map(s => `
                            <div class="card p-4 flex justify-between items-center" onclick="alert('הערה: ${s.notes || "אין"}')">
                                <div><p class="text-[9px] font-black text-cyan-600 uppercase">${s.jobName}</p><p class="text-xs font-bold">${s.start.split('T')[0]}</p></div>
                                <p class="font-black">₪${s.data.total_pay}</p>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            function renderJobsList(container) {
                container.innerHTML = jobs.map(j => `
                    <div class="card p-6 flex justify-between items-center mb-3" onclick="setView('job', ${j.id})">
                        <span class="font-black text-xl">${j.name} • <span class="text-xs opacity-40">${j.rate}₪</span></span>
                        <span class="material-icons opacity-20">chevron_left</span>
                    </div>
                `).join('') + (jobs.length === 0 ? '<p class="text-center opacity-30 py-20 text-sm">נא להוסיף עבודה בהגדרות</p>' : '');
            }

            function renderJobDetails(container, job) {
                const jShifts = shifts.filter(s => s.jobId == job.id).sort((a,b) => new Date(b.start) - new Date(a.start));
                const pay = jShifts.reduce((acc,s)=>acc+s.data.total_pay,0);
                const hours = jShifts.reduce((acc,s)=>acc+s.data.hours,0);

                container.innerHTML = `
                    <div class="flex gap-2 mb-4">
                        <button onclick="exportWA(${job.id})" class="flex-1 bg-green-600/20 text-green-500 py-3 rounded-2xl text-xs font-bold flex items-center justify-center gap-2">
                            <span class="material-icons text-sm">share</span> שלח סיכום שעות
                        </button>
                    </div>
                    <div class="space-y-3 pb-24">
                        ${jShifts.map(s => `
                            <div class="card p-5 flex justify-between items-center">
                                <div><p class="text-[10px] opacity-40">${s.start.split('T')[0]}</p><p class="font-bold">${s.start.split('T')[1]} - ${s.end.split('T')[1]}</p></div>
                                <div class="text-right"><p class="text-xl font-black text-cyan-600">₪${s.data.total_pay}</p><span class="text-[9px] text-red-400 font-bold" onclick="delShift(${s.id})">מחיקה</span></div>
                            </div>
                        `).join('')}
                    </div>
                    <footer class="glass fixed bottom-20 left-0 right-0 p-6 flex justify-around items-center border-t border-white/5 z-50">
                        <div class="text-center"><p class="text-[10px] font-bold opacity-40 uppercase">שעות</p><p class="text-xl font-black">${hours.toFixed(1)}</p></div>
                        <div class="text-center"><p class="text-[10px] font-bold opacity-40 uppercase">ברוטו</p><p class="text-xl font-black text-cyan-500">₪${pay.toLocaleString()}</p></div>
                    </footer>
                `;
            }

            function renderStats(container) {
                container.innerHTML = `
                    <div class="space-y-4">
                        ${jobs.map(j => {
                            const jShifts = shifts.filter(s => s.jobId == j.id);
                            const pay = jShifts.reduce((acc,s)=>acc+s.data.total_pay,0);
                            const hours = jShifts.reduce((acc,s)=>acc+s.data.hours,0);
                            const avg = hours > 0 ? (pay / hours).toFixed(1) : 0;
                            return `
                                <div class="card p-6">
                                    <div class="flex justify-between items-center mb-4">
                                        <h4 class="font-black text-lg">${j.name}</h4>
                                        <span class="bg-cyan-500/10 text-cyan-500 px-3 py-1 rounded-full text-[10px] font-black uppercase">₪${avg} / שעה</span>
                                    </div>
                                    <div class="grid grid-cols-2 gap-4">
                                        <div><p class="text-[10px] opacity-40 uppercase font-bold">סה"כ ברוטו</p><p class="font-black">₪${pay.toLocaleString()}</p></div>
                                        <div><p class="text-[10px] opacity-40 uppercase font-bold">סה"כ שעות</p><p class="font-black">${hours.toFixed(1)}</p></div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
            }

            function exportWA(id) {
                const job = jobs.find(j => j.id == id);
                const jShifts = shifts.filter(s => s.jobId == id);
                const pay = jShifts.reduce((acc,s)=>acc+s.data.total_pay,0);
                const hours = jShifts.reduce((acc,s)=>acc+s.data.hours,0);
                const text = `היי, מצורף סיכום שעות עבור ${job.name}:%0A%0Aסה"כ שעות: ${hours.toFixed(2)}%0Aשכר ברוטו צפוי: ₪${pay.toLocaleString()}%0A%0Aהופק באמצעות Smart Salary.`;
                window.open(`https://wa.me/?text=${text}`);
            }

            function openShiftModal() {
                if(jobs.length === 0) return alert('נא להוסיף עבודה תחילה');
                const sel = document.getElementById('s_job');
                sel.innerHTML = jobs.map(j => `<option value="${j.id}">${j.name}</option>`).join('');
                if(currentView === 'job') { sel.value = currentJobId; document.getElementById('job-sel-box').classList.add('hidden'); }
                else { document.getElementById('job-sel-box').classList.remove('hidden'); }
                document.getElementById('s_date').value = new Date().toISOString().split('T')[0];
                document.getElementById('shiftModal').style.display = 'flex';
            }

            function saveJob() {
                const name = document.getElementById('j_name').value;
                const rate = document.getElementById('j_rate').value;
                if(!name || !rate) return;
                jobs.push({ id: Date.now(), name, rate: parseFloat(rate) });
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
                        break_mins: parseInt(document.getElementById('s_break').value || 0)
                    })
                });
                const data = await res.json();
                shifts.push({ id: Date.now(), jobId, jobName: job.name, start, end, data, notes: document.getElementById('s_notes').value });
                localStorage.setItem('shifts', JSON.stringify(shifts));
                closeAll(); renderView();
            }

            function updateTheme(t) { document.body.className = t; localStorage.setItem('theme', t); }
            function saveGoal() { incomeGoal = document.getElementById('goal_amount').value; localStorage.setItem('incomeGoal', incomeGoal); renderView(); }
            function closeAll() { document.querySelectorAll('.modal').forEach(m => m.style.display='none'); }
            function renderJobsManager() { document.getElementById('jobs-manager-list').innerHTML = jobs.map(j => `<div class="card p-4 flex justify-between mb-2"><span>${j.name}</span><span class="material-icons text-red-400" onclick="delJob(${j.id})">delete</span></div>`).join(''); }
            function delJob(id) { if(confirm('למחוק?')) { jobs = jobs.filter(j=>j.id!=id); shifts = shifts.filter(s=>s.jobId!=id); localStorage.setItem('jobs', JSON.stringify(jobs)); localStorage.setItem('shifts', JSON.stringify(shifts)); renderJobsManager(); renderView(); } }
            function delShift(id) { if(confirm('למחוק?')) { shifts = shifts.filter(s=>s.id!=id); localStorage.setItem('shifts', JSON.stringify(shifts)); renderView(); } }
            function openSettings() { renderJobsManager(); document.getElementById('settingsModal').style.display = 'flex'; }
        </script>
    </body>
    </html>
    """

@app.post("/api/calculate")
async def calculate(shift: ShiftRequest):
    start = parser.isoparse(shift.start_time).astimezone(TIMEZONE)
    end = parser.isoparse(shift.end_time).astimezone(TIMEZONE)
    if end < start: end += timedelta(days=1)
    
    holidays = get_holidays(start.year)
    total_pay = 0
    curr = start
    step = timedelta(minutes=15)
    
    while curr < end:
        mult = 1.0
        # שבת / חג
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
    return {"total_pay": max(0, final_pay), "hours": (end-start).total_seconds()/3600 - (shift.break_mins/60)}
