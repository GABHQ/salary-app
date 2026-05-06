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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Salary Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            :root { --bg: #ffffff; --card: #f3f4f6; --text: #111827; --accent: #00acc1; }
            body.dark { --bg: #111827; --card: #1f2937; --text: #f9fafb; --accent: #26c6da; }
            body { background-color: var(--bg); color: var(--text); transition: 0.3s; }
            .card { background-color: var(--card); color: var(--text); }
            .drawer { background-color: var(--bg); color: var(--text); }
            /* כפייה של המשתנים על אלמנטים של Tailwind */
            .bg-white, .bg-gray-100 { background-color: var(--bg) !important; }
            .text-gray-800, .text-gray-900 { color: var(--text) !important; }
        </style>
    </head>
    <body class="font-sans">

        <div id="drawer" class="fixed inset-y-0 right-0 w-72 bg-white shadow-2xl z-[300] transform translate-x-full transition-transform duration-300 dark:bg-gray-900">
            <div class="p-6">
                <div class="flex justify-between items-center mb-8">
                    <h2 class="text-xl font-bold border-b-2 border-cyan-500 pb-1">תפריט</h2>
                    <span class="material-icons cursor-pointer" onclick="toggleDrawer()">close</span>
                </div>
                <nav class="space-y-4">
                    <button onclick="setView('home')" class="w-full text-right p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 flex items-center gap-3">
                        <span class="material-icons text-cyan-600">home</span> דף הבית
                    </button>
                    <div id="jobs-menu-list" class="space-y-2"></div>
                    <button onclick="openSettings()" class="w-full text-right p-3 mt-4 border-t flex items-center gap-3">
                        <span class="material-icons text-gray-400">settings</span> הגדרות
                    </button>
                </nav>
            </div>
        </div>
        <div id="overlay" class="fixed inset-0 bg-black/50 z-[250] hidden" onclick="closeAll()"></div>

        <header class="bg-cyan-600 text-white p-4 shadow-md flex justify-between items-center sticky top-0 z-50">
            <span class="material-icons p-2 cursor-pointer" onclick="toggleDrawer()">menu</span>
            <h1 id="view-title" class="text-lg font-bold">סקירה כללית</h1>
            <span class="material-icons p-2 cursor-pointer" onclick="openShiftModal()">add</span>
        </header>

        <main class="p-4 pb-32">
            <section id="view-home">
                <div class="card p-8 mb-6 text-center rounded-2xl border-t-4 border-cyan-500 shadow-sm">
                    <p class="text-[10px] uppercase font-bold opacity-50 mb-1">הכנסה חודשית ברוטו</p>
                    <p class="text-4xl font-black text-cyan-600">₪ <span id="home-total-money">0.00</span></p>
                </div>
                <h3 class="font-bold mb-4 flex items-center gap-2 text-sm opacity-70">תיעודים אחרונים</h3>
                <div id="global-history" class="space-y-3"></div>
            </section>

            <section id="view-job" class="hidden">
                <div id="job-shift-list" class="space-y-3"></div>
            </section>
        </main>

        <footer id="job-footer" class="fixed bottom-0 left-0 right-0 bg-cyan-700 text-white p-4 flex justify-around font-bold shadow-2xl hidden z-40">
            <div class="text-center"><p class="text-[10px] opacity-70 uppercase">שעות</p><span id="job-total-hours">0.00</span></div>
            <div class="text-center"><p class="text-[10px] opacity-70 uppercase">שכר צפוי</p>₪ <span id="job-total-pay">0.00</span></div>
        </footer>

        <div id="settingsModal" class="modal" onclick="if(event.target==this)closeModal('settingsModal')">
            <div class="modal-content">
                <h2 class="font-bold mb-4 border-b pb-2">הגדרות וניהול עבודות</h2>
                <div id="jobs-manager-list" class="space-y-2 mb-6"></div>
                <div class="card p-4 rounded-xl mb-6">
                    <p class="font-bold text-xs mb-3 uppercase opacity-60">הוספת עבודה</p>
                    <input id="j_name" placeholder="שם העבודה" class="w-full p-3 rounded-lg mb-2 text-sm">
                    <div class="flex gap-2">
                        <select id="j_type" class="w-1/3 p-3 rounded-lg text-sm">
                            <option value="hourly">שעתי</option>
                            <option value="monthly">גלובלי</option>
                        </select>
                        <input id="j_rate" type="number" placeholder="תעריף" class="w-full p-3 rounded-lg text-sm">
                        <button onclick="saveJob()" class="bg-cyan-600 text-white px-4 rounded-lg font-bold">שמור</button>
                    </div>
                </div>
                <div class="space-y-4 border-t pt-4">
                    <select id="theme-select" onchange="setTheme(this.value)" class="w-full p-3 rounded-lg">
                        <option value="light">מצב בהיר ☀️</option>
                        <option value="dark">מצב כהה 🌙</option>
                    </select>
                </div>
                <button onclick="closeModal('settingsModal')" class="w-full mt-8 py-4 bg-gray-100 dark:bg-gray-800 rounded-xl font-bold">סגור</button>
            </div>
        </div>

        <div id="shiftModal" class="modal" onclick="if(event.target==this)closeModal('shiftModal')">
            <div class="modal-content">
                <h2 class="font-bold mb-4 text-center text-cyan-600 uppercase tracking-widest text-sm">תיעוד משמרת</h2>
                <div class="space-y-4">
                    <select id="s_job" class="w-full p-3 rounded-lg"></select>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="date" id="s_date" class="w-full p-3 rounded-lg text-sm">
                        <input type="number" id="s_rate_override" placeholder="תעריף" class="w-full p-3 rounded-lg text-sm">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <div class="card p-2 rounded-lg"><label class="text-[10px] block opacity-50">כניסה</label><input type="time" id="s_start" class="w-full border-none p-1"></div>
                        <div class="card p-2 rounded-lg"><label class="text-[10px] block opacity-50">יציאה</label><input type="time" id="s_end" class="w-full border-none p-1"></div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="number" id="s_break" placeholder="הפסקה (דקות)" class="w-full p-3 rounded-lg text-sm">
                        <input type="number" id="s_extra" placeholder="בונוס/נסיעות" class="w-full p-3 rounded-lg text-sm">
                    </div>
                    <button onclick="saveShift()" class="w-full bg-cyan-600 text-white py-4 rounded-xl font-bold shadow-lg mt-4">שמור משמרת</button>
                </div>
            </div>
        </div>

        <script>
            let jobs = JSON.parse(localStorage.getItem('jobs')) || [];
            let shifts = JSON.parse(localStorage.getItem('shifts')) || [];
            let currentView = 'home';
            let currentJobId = null;

            window.onload = () => {
                const theme = localStorage.getItem('theme') || 'light';
                setTheme(theme);
                document.getElementById('theme-select').value = theme;
                document.getElementById('s_date').value = new Date().toISOString().split('T')[0];
                renderView();
            };

            function toggleDrawer() {
                const d = document.getElementById('drawer');
                const o = document.getElementById('overlay');
                const isOpen = d.classList.contains('translate-x-0');
                d.classList.toggle('translate-x-0', !isOpen);
                d.classList.toggle('translate-x-full', isOpen);
                o.classList.toggle('hidden', isOpen);
            }

            function closeAll() {
                if(!document.getElementById('drawer').classList.contains('translate-x-full')) toggleDrawer();
                closeModal('settingsModal');
                closeModal('shiftModal');
            }

            function closeModal(id) { 
                document.getElementById(id).style.display = 'none'; 
                document.getElementById('overlay').classList.add('hidden');
            }

            function openSettings() { 
                renderJobsManager();
                document.getElementById('settingsModal').style.display = 'flex'; 
                document.getElementById('overlay').classList.remove('hidden');
                if(!document.getElementById('drawer').classList.contains('translate-x-full')) toggleDrawer();
            }

            function openShiftModal() {
                if(jobs.length === 0) return alert('נא להוסיף עבודה בהגדרות תחילה');
                updateJobSelects();
                document.getElementById('shiftModal').style.display = 'flex';
                document.getElementById('overlay').classList.remove('hidden');
            }

            function saveJob() {
                const name = document.getElementById('j_name').value;
                const rate = document.getElementById('j_rate').value;
                const type = document.getElementById('j_type').value;
                if(!name || !rate) return alert('נא למלא את כל השדות');
                jobs.push({ id: Date.now(), name, rate: parseFloat(rate), type });
                localStorage.setItem('jobs', JSON.stringify(jobs));
                document.getElementById('j_name').value = '';
                document.getElementById('j_rate').value = '';
                renderJobsManager();
                renderView();
            }

            function deleteJob(id) {
                if(!confirm('למחוק עבודה זו ואת כל המשמרות שלה?')) return;
                jobs = jobs.filter(j => j.id !== id);
                shifts = shifts.filter(s => s.jobId != id);
                localStorage.setItem('jobs', JSON.stringify(jobs));
                localStorage.setItem('shifts', JSON.stringify(shifts));
                renderJobsManager();
                renderView();
            }

            function renderJobsMenu() {
                const list = document.getElementById('jobs-menu-list');
                list.innerHTML = jobs.map(j => `
                    <div class="flex items-center gap-2 w-full p-1">
                        <button onclick="setView('job', ${j.id})" class="flex-1 text-right p-3 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-sm font-medium">
                            ${j.name} <span class="opacity-40 mx-1">•</span> <span class="text-[10px] opacity-60 uppercase">${j.type === 'hourly' ? 'שעתי' : 'גלובלי'}</span>
                        </button>
                        <span class="material-icons text-xs text-gray-300 p-2 cursor-pointer" onclick="openSettings()">edit</span>
                    </div>
                `).join('');
            }

            function renderJobsManager() {
                const list = document.getElementById('jobs-manager-list');
                list.innerHTML = jobs.map(j => `
                    <div class="card flex justify-between items-center p-4 rounded-xl mb-2">
                        <span class="font-bold">${j.name} (${j.rate}₪)</span>
                        <span class="material-icons text-red-400 cursor-pointer" onclick="deleteJob(${j.id})">delete</span>
                    </div>
                `).join('');
            }

            function updateJobSelects() {
                const select = document.getElementById('s_job');
                select.innerHTML = jobs.map(j => `<option value="${j.id}">${j.name}</option>`).join('');
                if(jobs.length > 0) document.getElementById('s_rate_override').value = jobs[0].rate;
            }

            function setView(view, jobId = null) {
                currentView = view;
                currentJobId = jobId;
                closeAll();
                renderView();
            }

            async function saveShift() {
                const jobId = document.getElementById('s_job').value;
                const job = jobs.find(j => j.id == jobId);
                const start = document.getElementById('s_date').value + 'T' + document.getElementById('s_start').value;
                const end = document.getElementById('s_date').value + 'T' + document.getElementById('s_end').value;
                const rate = document.getElementById('s_rate_override').value || job.rate;

                try {
                    const res = await fetch('/api/calculate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            start_time: start, end_time: end, base_rate: parseFloat(rate),
                            break_mins: parseInt(document.getElementById('s_break').value || 0),
                            extra_pay: parseFloat(document.getElementById('s_extra').value || 0)
                        })
                    });
                    const data = await res.json();
                    shifts.push({ id: Date.now(), jobId, jobName: job.name, start, end, data });
                    localStorage.setItem('shifts', JSON.stringify(shifts));
                    renderView();
                    closeAll();
                } catch(e) { alert('שגיאה בחישוב השכר'); }
            }

            function renderView() {
                renderJobsMenu();
                document.getElementById('view-home').classList.toggle('hidden', currentView !== 'home');
                document.getElementById('view-job').classList.toggle('hidden', currentView !== 'job');
                document.getElementById('job-footer').classList.toggle('hidden', currentView !== 'job');

                if (currentView === 'home') {
                    document.getElementById('view-title').innerText = 'סקירה כללית';
                    const total = shifts.reduce((acc, s) => acc + s.data.total_pay, 0);
                    document.getElementById('home-total-money').innerText = total.toLocaleString();
                    const history = [...shifts].sort((a,b) => new Date(b.start) - new Date(a.start)).slice(0, 10);
                    document.getElementById('global-history').innerHTML = history.map(s => `
                        <div class="card p-4 flex justify-between items-center rounded-xl shadow-sm">
                            <div><p class="text-[9px] font-black text-cyan-600 uppercase tracking-tighter">${s.jobName}</p><p class="text-[11px] opacity-50">${s.start.split('T')[0]}</p></div>
                            <div class="font-bold text-lg">₪${s.data.total_pay}</div>
                        </div>
                    `).join('');
                } else {
                    const job = jobs.find(j => j.id == currentJobId);
                    document.getElementById('view-title').innerText = job.name;
                    const jobShifts = shifts.filter(s => s.jobId == currentJobId).sort((a,b) => new Date(b.start) - new Date(a.start));
                    document.getElementById('job-shift-list').innerHTML = jobShifts.map(s => `
                        <div class="card p-4 flex justify-between items-center rounded-xl">
                            <div><p class="text-[10px] opacity-40">${s.start.split('T')[0]}</p><p class="font-bold text-sm">${s.start.split('T')[1]} - ${s.end.split('T')[1]}</p></div>
                            <div class="text-right">
                                <p class="text-lg font-black text-cyan-600">₪${s.data.total_pay}</p>
                                <button onclick="deleteShift(${s.id})" class="text-[9px] text-red-400 font-bold uppercase">מחיקה</button>
                            </div>
                        </div>
                    `).join('');
                    document.getElementById('job-total-hours').innerText = jobShifts.reduce((acc, s) => acc + s.data.hours, 0).toFixed(2);
                    document.getElementById('job-total-pay').innerText = jobShifts.reduce((acc, s) => acc + s.data.total_pay, 0).toLocaleString();
                }
            }

            function deleteShift(id) {
                if(!confirm('למחוק משמרת זו?')) return;
                shifts = shifts.filter(s => s.id !== id);
                localStorage.setItem('shifts', JSON.stringify(shifts));
                renderView();
            }

            function setTheme(t) {
                document.body.classList.toggle('dark', t === 'dark');
                localStorage.setItem('theme', t);
            }
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
        if (curr.weekday() == 4 and curr.hour >= 18) or (curr.weekday() == 5 and curr.hour < 20):
            mult = 1.5
        for h in holidays:
            if h.get('date') == curr.strftime('%Y-%m-%d'):
                mult = 1.5 if "Erev" in h.get('title', '') else 2.0
                break
        total_pay += (shift.base_rate * mult) * (15/60)
        curr += step
    deduction = (shift.break_mins / 60) * shift.base_rate
    final = round(total_pay - deduction + shift.extra_pay, 2)
    return {"total_pay": max(0, final), "hours": (end-start).total_seconds()/3600}
