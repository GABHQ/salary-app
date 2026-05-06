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
            :root { --main-bg: #f3f4f6; --card-bg: #ffffff; --text-main: #1f2937; --accent: #00acc1; --font-size: 16px; }
            body.dark { --main-bg: #111827; --card-bg: #1f2937; --text-main: #f9fafb; --accent: #26c6da; }
            body { background-color: var(--main-bg); color: var(--text-main); font-size: var(--font-size); transition: 0.3s; margin: 0; }
            .card { background-color: var(--card-bg); border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); align-items: flex-end; z-index: 200; }
            .modal-content { background: var(--card-bg); width: 100%; border-radius: 20px 20px 0 0; padding: 20px; max-height: 90vh; overflow-y: auto; color: var(--text-main); }
            .hidden { display: none; }
        </style>
    </head>
    <body class="font-sans">

        <div id="drawer" class="fixed inset-y-0 right-0 w-72 bg-white shadow-2xl z-[250] transform translate-x-full transition-transform duration-300 dark:bg-gray-800 text-gray-800 dark:text-white">
            <div class="p-6">
                <div class="flex justify-between items-center mb-8">
                    <h2 class="text-xl font-bold border-b-2 border-cyan-500 pb-1">תפריט</h2>
                    <span class="material-icons cursor-pointer" onclick="toggleDrawer()">close</span>
                </div>
                <nav class="space-y-2">
                    <button onclick="setView('home')" class="w-full text-right p-3 rounded-lg hover:bg-cyan-50 flex items-center gap-3 dark:hover:bg-gray-700">
                        <span class="material-icons text-cyan-600">home</span> דף הבית
                    </button>
                    <div id="jobs-menu-list" class="pt-4 space-y-2">
                        </div>
                    <div class="border-t mt-4 pt-4">
                        <button onclick="openSettings()" class="w-full text-right p-3 rounded-lg hover:bg-gray-100 flex items-center gap-3 dark:hover:bg-gray-700">
                            <span class="material-icons">settings</span> הגדרות
                        </button>
                    </div>
                </nav>
            </div>
        </div>
        <div id="overlay" class="fixed inset-0 bg-black/50 z-[240] hidden" onclick="toggleDrawer()"></div>

        <header class="bg-cyan-600 text-white p-4 shadow-md flex justify-between items-center sticky top-0 z-50">
            <span class="material-icons p-2 cursor-pointer" onclick="toggleDrawer()">menu</span>
            <h1 id="view-title" class="text-lg font-bold">סקירה כללית</h1>
            <span class="material-icons p-2 cursor-pointer" onclick="openShiftModal()">add</span>
        </header>

        <main class="p-4 pb-32">
            <section id="view-home">
                <div class="card p-8 mb-6 text-center border-t-4 border-cyan-500">
                    <p class="text-xs uppercase tracking-wider opacity-60">הכנסה חודשית כוללת</p>
                    <p class="text-4xl font-black mt-2 text-cyan-600">₪ <span id="home-total-money">0.00</span></p>
                </div>
                <h3 class="font-bold mb-4 flex items-center gap-2">תיעודים אחרונים</h3>
                <div id="global-history" class="space-y-3"></div>
            </section>

            <section id="view-job" class="hidden">
                <div id="job-shift-list" class="space-y-3"></div>
            </section>
        </main>

        <footer id="job-footer" class="fixed bottom-0 left-0 right-0 bg-cyan-700 text-white p-4 flex justify-around font-bold shadow-2xl hidden">
            <div class="text-center"><p class="text-[10px] opacity-70">שעות</p><span id="job-total-hours">0.00</span></div>
            <div class="text-center"><p class="text-[10px] opacity-70">סה"כ שכר</p>₪ <span id="job-total-pay">0.00</span></div>
        </footer>

        <div id="settingsModal" class="modal"><div class="modal-content">
            <h2 class="font-bold mb-4 border-b pb-2">הגדרות וניהול עבודות</h2>
            <div id="jobs-manager-list" class="space-y-2 mb-6"></div>
            <div class="bg-gray-50 p-4 rounded-lg dark:bg-gray-700 mb-6">
                <p class="font-bold text-sm mb-3">הוספת עבודה חדשה</p>
                <input id="j_name" placeholder="שם העבודה (למשל: גוסטה)" class="w-full border p-2 rounded mb-2 dark:bg-gray-600 text-sm">
                <div class="flex gap-2">
                    <input id="j_rate" type="number" placeholder="שכר שעתי" class="w-full border p-2 rounded dark:bg-gray-600 text-sm">
                    <button onclick="saveJob()" class="bg-cyan-600 text-white px-4 rounded font-bold">שמור</button>
                </div>
            </div>
            <div class="space-y-4 border-t pt-4">
                <p class="text-xs font-bold text-gray-400">עיצוב</p>
                <select onchange="setTheme(this.value)" class="w-full border p-2 rounded dark:bg-gray-600">
                    <option value="light">מצב בהיר</option>
                    <option value="dark">מצב כהה</option>
                </select>
            </div>
            <button onclick="closeModal('settingsModal')" class="w-full mt-8 py-3 bg-gray-200 rounded-lg dark:bg-gray-600">סגור</button>
        </div></div>

        <div id="shiftModal" class="modal"><div class="modal-content">
            <h2 class="font-bold mb-4 text-center text-cyan-600">הוספת משמרת</h2>
            <div class="space-y-4">
                <div><label class="text-xs">בחר עבודה:</label><select id="s_job" class="w-full border p-2 rounded dark:bg-gray-700"></select></div>
                <div class="grid grid-cols-2 gap-2">
                    <div><label class="text-xs">תאריך:</label><input type="date" id="s_date" class="w-full border p-2 rounded dark:bg-gray-700"></div>
                    <div><label class="text-xs">שכר שעתי:</label><input type="number" id="s_rate_override" class="w-full border p-2 rounded dark:bg-gray-700"></div>
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div><label class="text-xs">כניסה:</label><input type="time" id="s_start" class="w-full border p-2 rounded dark:bg-gray-700"></div>
                    <div><label class="text-xs">יציאה:</label><input type="time" id="s_end" class="w-full border p-2 rounded dark:bg-gray-700"></div>
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <div><label class="text-xs">הפסקה (דקות):</label><input type="number" id="s_break" value="0" class="w-full border p-2 rounded dark:bg-gray-700"></div>
                    <div><label class="text-xs">בונוס/נסיעות (₪):</label><input type="number" id="s_extra" value="0" class="w-full border p-2 rounded dark:bg-gray-700"></div>
                </div>
                <div class="flex gap-2 pt-4">
                    <button onclick="saveShift()" class="flex-1 bg-cyan-600 text-white py-3 rounded-lg font-bold">שמור</button>
                    <button onclick="closeModal('shiftModal')" class="flex-1 bg-gray-200 py-3 rounded-lg dark:bg-gray-700">ביטול</button>
                </div>
            </div>
        </div></div>

        <script>
            let jobs = JSON.parse(localStorage.getItem('jobs')) || [];
            let shifts = JSON.parse(localStorage.getItem('shifts')) || [];
            let currentView = 'home';
            let currentJobId = null;

            window.onload = () => {
                document.getElementById('s_date').value = new Date().toISOString().split('T')[0];
                if(localStorage.getItem('theme') === 'dark') document.body.classList.add('dark');
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

            function setView(view, jobId = null) {
                currentView = view;
                currentJobId = jobId;
                if(document.getElementById('drawer').classList.contains('translate-x-0')) toggleDrawer();
                renderView();
            }

            function openShiftModal() {
                if(jobs.length === 0) return alert('קודם כל תגדיר מקום עבודה בהגדרות');
                updateJobSelects();
                document.getElementById('shiftModal').style.display = 'flex';
            }

            function openSettings() { 
                renderJobsManager();
                document.getElementById('settingsModal').style.display = 'flex'; 
            }

            function closeModal(id) { document.getElementById(id).style.display = 'none'; }

            function saveJob() {
                const name = document.getElementById('j_name').value;
                const rate = document.getElementById('j_rate').value;
                if(!name || !rate) return alert('מלא את כל השדות');
                jobs.push({ id: Date.now(), name, rate: parseFloat(rate) });
                localStorage.setItem('jobs', JSON.stringify(jobs));
                document.getElementById('j_name').value = '';
                document.getElementById('j_rate').value = '';
                renderJobsManager();
                renderJobsMenu();
                updateJobSelects();
            }

            function deleteJob(id) {
                jobs = jobs.filter(j => j.id !== id);
                shifts = shifts.filter(s => s.jobId != id);
                localStorage.setItem('jobs', JSON.stringify(jobs));
                localStorage.setItem('shifts', JSON.stringify(shifts));
                renderJobsManager();
                renderJobsMenu();
                renderView();
            }

            function renderJobsMenu() {
                const list = document.getElementById('jobs-menu-list');
                list.innerHTML = jobs.map(j => `
                    <button onclick="setView('job', ${j.id})" class="w-full text-right p-3 rounded-lg hover:bg-cyan-50 flex items-center gap-3 dark:hover:bg-gray-700">
                        <span class="material-icons text-xs text-cyan-400">circle</span> ${j.name}
                    </button>
                `).join('');
            }

            function renderJobsManager() {
                const list = document.getElementById('jobs-manager-list');
                list.innerHTML = jobs.map(j => `
                    <div class="flex justify-between items-center p-3 bg-gray-100 rounded dark:bg-gray-800">
                        <span>${j.name} (${j.rate}₪)</span>
                        <span class="material-icons text-red-400 cursor-pointer" onclick="deleteJob(${j.id})">delete</span>
                    </div>
                `).join('');
            }

            function updateJobSelects() {
                const select = document.getElementById('s_job');
                select.innerHTML = jobs.map(j => `<option value="${j.id}">${j.name}</option>`).join('');
                if(jobs.length > 0) document.getElementById('s_rate_override').value = jobs[0].rate;
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
                            break_mins: parseInt(document.getElementById('s_break').value),
                            extra_pay: parseFloat(document.getElementById('s_extra').value)
                        })
                    });
                    const data = await res.json();
                    shifts.push({ id: Date.now(), jobId, jobName: job.name, start, end, data });
                    localStorage.setItem('shifts', JSON.stringify(shifts));
                    renderView();
                    closeModal('shiftModal');
                } catch(e) { alert('שגיאה בחישוב'); }
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
                        <div class="card p-4 flex justify-between items-center border-r-4 border-cyan-500">
                            <div><p class="text-[10px] font-bold text-cyan-600">${s.jobName}</p><p class="text-xs opacity-60">${s.start.split('T')[0]}</p></div>
                            <div class="font-bold">₪${s.data.total_pay}</div>
                        </div>
                    `).join('');
                } else {
                    const job = jobs.find(j => j.id == currentJobId);
                    document.getElementById('view-title').innerText = job.name;
                    const jobShifts = shifts.filter(s => s.jobId == currentJobId).sort((a,b) => new Date(b.start) - new Date(a.start));
                    document.getElementById('job-shift-list').innerHTML = jobShifts.map(s => `
                        <div class="card p-4 flex justify-between items-center">
                            <div><p class="text-xs opacity-60">${s.start.split('T')[0]}</p><p class="font-bold">${s.start.split('T')[1]} - ${s.end.split('T')[1]}</p></div>
                            <div class="text-right"><p class="text-xl font-bold text-cyan-600">₪${s.data.total_pay}</p>
                            <span class="text-[10px] text-red-300" onclick="deleteShift(${s.id})">מחק</span></div>
                        </div>
                    `).join('');
                    document.getElementById('job-total-hours').innerText = jobShifts.reduce((acc, s) => acc + s.data.hours, 0).toFixed(2);
                    document.getElementById('job-total-pay').innerText = jobShifts.reduce((acc, s) => acc + s.data.total_pay, 0).toLocaleString();
                }
            }

            function deleteShift(id) {
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
