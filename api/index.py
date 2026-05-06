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
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Smart Salary 2026</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            :root { --bg: #ffffff; --card: #f9fafb; --text: #111827; --accent: #00acc1; --nav-bg: #ffffff; }
            body.dark { --bg: #111827; --card: #1f2937; --text: #f9fafb; --accent: #26c6da; --nav-bg: #1f2937; }
            
            body { background-color: var(--bg); color: var(--text); transition: 0.3s; margin: 0; padding-bottom: 80px; }
            .card { background-color: var(--card); border: 1px solid rgba(0,0,0,0.05); color: var(--text); }
            .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); align-items: flex-end; z-index: 500; }
            .modal-content { background: var(--bg); color: var(--text); border-radius: 24px 24px 0 0; padding: 24px; width: 100%; }
            
            /* Bottom Nav Styles */
            .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: var(--nav-bg); height: 70px; display: flex; justify-content: space-around; align-items: center; border-top: 1px solid rgba(0,0,0,0.1); z-index: 400; box-shadow: 0 -2px 10px rgba(0,0,0,0.05); }
            .nav-item { display: flex; flex-direction: column; align-items: center; color: var(--text); opacity: 0.5; transition: 0.2s; cursor: pointer; }
            .nav-item.active { opacity: 1; color: var(--accent); }
            .nav-item span { font-size: 24px; }
            .nav-item p { font-size: 10px; font-weight: bold; margin-top: 2px; }

            input, select { background: var(--card) !important; color: var(--text) !important; border: 1px solid rgba(0,0,0,0.1) !important; outline: none; }
            .hidden { display: none; }
        </style>
    </head>
    <body class="font-sans">

        <header class="bg-cyan-600 text-white p-4 shadow-md flex justify-between items-center sticky top-0 z-50">
            <h1 id="view-title" class="text-lg font-bold">סקירה כללית</h1>
            <span class="material-icons cursor-pointer" onclick="openShiftModal()">add_circle</span>
        </header>

        <main class="p-4">
            <section id="view-home">
                <div class="card p-8 mb-6 text-center rounded-2xl border-t-4 border-cyan-500">
                    <p class="text-[10px] uppercase font-bold opacity-50 mb-1">הכנסה כוללת החודש</p>
                    <p class="text-4xl font-black text-cyan-600">₪ <span id="home-total-money">0.00</span></p>
                </div>
                <h3 class="font-bold mb-4 text-sm opacity-70">פעולות אחרונות</h3>
                <div id="global-history" class="space-y-3"></div>
            </section>

            <section id="view-jobs" class="hidden">
                <h3 class="font-bold mb-4">מקומות העבודה שלי</h3>
                <div id="jobs-list-display" class="space-y-3"></div>
            </section>

            <section id="view-job-details" class="hidden">
                <div id="job-shift-list" class="space-y-3"></div>
                <div class="card p-4 mt-6 flex justify-around font-bold rounded-xl border-b-4 border-cyan-500">
                    <div class="text-center"><p class="text-[10px] opacity-50">שעות</p><span id="job-total-hours">0.00</span></div>
                    <div class="text-center"><p class="text-[10px] opacity-50">שכר</p>₪ <span id="job-total-pay">0.00</span></div>
                </div>
            </section>
        </main>

        <nav class="bottom-nav">
            <div class="nav-item active" onclick="setView('home')" id="nav-home">
                <span class="material-icons">dashboard</span>
                <p>ראשי</p>
            </div>
            <div class="nav-item" onclick="setView('jobs')" id="nav-jobs">
                <span class="material-icons">work</span>
                <p>עבודות</p>
            </div>
            <div class="nav-item" id="nav-stats">
                <span class="material-icons">analytics</span>
                <p>השוואה</p>
            </div>
            <div class="nav-item" onclick="openSettings()" id="nav-settings">
                <span class="material-icons">settings</span>
                <p>הגדרות</p>
            </div>
        </nav>

        <div id="settingsModal" class="modal" onclick="if(event.target==this)closeAll()">
            <div class="modal-content">
                <h2 class="font-bold mb-4 border-b pb-2">הגדרות וניהול עבודות</h2>
                <div id="jobs-manager-list" class="space-y-2 mb-6"></div>
                <div class="card p-4 rounded-xl mb-4">
                    <p class="font-bold text-xs mb-3 opacity-50">הוספת עבודה</p>
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
                <select onchange="setTheme(this.value)" class="w-full p-3 rounded-lg mt-4">
                    <option value="light">מצב בהיר ☀️</option>
                    <option value="dark">מצב כהה 🌙</option>
                </select>
                <button onclick="closeAll()" class="w-full mt-6 py-4 bg-gray-100 dark:bg-gray-800 rounded-xl font-bold">סגור</button>
            </div>
        </div>

        <div id="shiftModal" class="modal" onclick="if(event.target==this)closeAll()">
            <div class="modal-content">
                <h2 class="font-bold mb-4 text-center text-cyan-600">תיעוד משמרת</h2>
                <div class="space-y-4">
                    <select id="s_job" class="w-full p-3 rounded-lg"></select>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="date" id="s_date" class="w-full p-3 rounded-lg text-sm">
                        <input type="number" id="s_rate_override" placeholder="תעריף" class="w-full p-3 rounded-lg text-sm">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="time" id="s_start" class="w-full p-3 rounded-lg">
                        <input type="time" id="s_end" class="w-full p-3 rounded-lg">
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="number" id="s_break" placeholder="הפסקה (דק')" class="w-full p-3 rounded-lg text-sm">
                        <input type="number" id="s_extra" placeholder="בונוס" class="w-full p-3 rounded-lg text-sm">
                    </div>
                    <button onclick="saveShift()" class="w-full bg-cyan-600 text-white py-4 rounded-xl font-bold mt-4">שמור</button>
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
                document.getElementById('s_date').value = new Date().toISOString().split('T')[0];
                renderView();
            };

            function setView(view, jobId = null) {
                currentView = view;
                currentJobId = jobId;
                renderView();
            }

            function renderView() {
                // ניהול נראות מסכים
                document.getElementById('view-home').classList.toggle('hidden', currentView !== 'home');
                document.getElementById('view-jobs').classList.toggle('hidden', currentView !== 'jobs');
                document.getElementById('view-job-details').classList.toggle('hidden', currentView !== 'job');
                
                // עדכון אקטיביות בתפריט התחתון
                document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
                if(currentView === 'home') document.getElementById('nav-home').classList.add('active');
                if(currentView === 'jobs' || currentView === 'job') document.getElementById('nav-jobs').classList.add('active');

                if (currentView === 'home') {
                    document.getElementById('view-title').innerText = 'סקירה כללית';
                    renderHome();
                } else if (currentView === 'jobs') {
                    document.getElementById('view-title').innerText = 'העבודות שלי';
                    renderJobsList();
                } else {
                    const job = jobs.find(j => j.id == currentJobId);
                    document.getElementById('view-title').innerText = job.name;
                    renderJobDetails();
                }
            }

            function renderHome() {
                const total = shifts.reduce((acc, s) => acc + s.data.total_pay, 0);
                document.getElementById('home-total-money').innerText = total.toLocaleString();
                const history = [...shifts].sort((a,b) => new Date(b.start) - new Date(a.start)).slice(0, 10);
                document.getElementById('global-history').innerHTML = history.map(s => `
                    <div class="card p-4 flex justify-between items-center rounded-xl mb-2">
                        <div><p class="text-[9px] font-bold text-cyan-600 uppercase">${s.jobName}</p><p class="text-xs opacity-50">${s.start.split('T')[0]}</p></div>
                        <div class="font-bold text-lg">₪${s.data.total_pay}</div>
                    </div>
                `).join('');
            }

            function renderJobsList() {
                const container = document.getElementById('jobs-list-display');
                container.innerHTML = jobs.map(j => `
                    <div class="card p-4 rounded-xl flex justify-between items-center" onclick="setView('job', ${j.id})">
                        <div>
                            <p class="font-bold">${j.name} <span class="opacity-30 mx-1">•</span> <span class="text-[10px] opacity-60 uppercase">${j.type === 'hourly' ? 'שעתי' : 'גלובלי'}</span></p>
                        </div>
                        <span class="material-icons opacity-30 text-sm">chevron_left</span>
                    </div>
                `).join('');
            }

            function renderJobDetails() {
                const jobShifts = shifts.filter(s => s.jobId == currentJobId).sort((a,b) => new Date(b.start) - new Date(a.start));
                document.getElementById('job-shift-list').innerHTML = jobShifts.map(s => `
                    <div class="card p-4 flex justify-between items-center rounded-xl">
                        <div><p class="text-xs opacity-40">${s.start.split('T')[0]}</p><p class="font-bold text-sm">${s.start.split('T')[1]} - ${s.end.split('T')[1]}</p></div>
                        <div class="text-right">
                            <p class="text-lg font-black text-cyan-600">₪${s.data.total_pay}</p>
                            <button onclick="deleteShift(${s.id})" class="text-[9px] text-red-400 font-bold uppercase">מחיקה</button>
                        </div>
                    </div>
                `).join('');
                document.getElementById('job-total-hours').innerText = jobShifts.reduce((acc, s) => acc + s.data.hours, 0).toFixed(2);
                document.getElementById('job-total-pay').innerText = jobShifts.reduce((acc, s) => acc + s.data.total_pay, 0).toLocaleString();
            }

            function openShiftModal() {
                if(jobs.length === 0) return alert('נא להוסיף עבודה בהגדרות');
                const select = document.getElementById('s_job');
                select.innerHTML = jobs.map(j => `<option value="${j.id}">${j.name}</option>`).join('');
                document.getElementById('shiftModal').style.display = 'flex';
            }

            function openSettings() { renderJobsManager(); document.getElementById('settingsModal').style.display = 'flex'; }
            function closeAll() { document.getElementById('settingsModal').style.display = 'none'; document.getElementById('shiftModal').style.display = 'none'; }
            
            function saveJob() {
                const name = document.getElementById('j_name').value;
                const rate = document.getElementById('j_rate').value;
                const type = document.getElementById('j_type').value;
                if(!name || !rate) return;
                jobs.push({ id: Date.now(), name, rate: parseFloat(rate), type });
                localStorage.setItem('jobs', JSON.stringify(jobs));
                document.getElementById('j_name').value = '';
                document.getElementById('j_rate').value = '';
                renderJobsManager();
                renderView();
            }

            function renderJobsManager() {
                document.getElementById('jobs-manager-list').innerHTML = jobs.map(j => `
                    <div class="card flex justify-between items-center p-3 rounded-lg mb-2">
                        <span class="text-sm font-bold">${j.name} (${j.rate}₪)</span>
                        <span class="material-icons text-red-400 text-sm cursor-pointer" onclick="deleteJob(${j.id})">delete</span>
                    </div>
                `).join('');
            }

            function deleteJob(id) {
                if(confirm('למחוק עבודה זו?')) {
                    jobs = jobs.filter(j => j.id !== id);
                    shifts = shifts.filter(s => s.jobId != id);
                    localStorage.setItem('jobs', JSON.stringify(jobs));
                    localStorage.setItem('shifts', JSON.stringify(shifts));
                    renderJobsManager();
                    renderView();
                }
            }

            async function saveShift() {
                const jobId = document.getElementById('s_job').value;
                const job = jobs.find(j => j.id == jobId);
                const start = document.getElementById('s_date').value + 'T' + document.getElementById('s_start').value;
                const end = document.getElementById('s_date').value + 'T' + document.getElementById('s_end').value;
                const rate = document.getElementById('s_rate_override').value || job.rate;

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
