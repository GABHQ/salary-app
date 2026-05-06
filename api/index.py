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
    try: return requests.get(url).json().get('items', [])
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
            body { background-color: var(--main-bg); color: var(--text-main); font-size: var(--font-size); transition: 0.3s; }
            .card { background-color: var(--card-bg); border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .header { background-color: var(--accent); color: white; }
            .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); align-items: flex-end; z-index: 100; }
            .modal-content { background: var(--card-bg); width: 100%; border-radius: 20px 20px 0 0; padding: 20px; max-height: 90vh; overflow-y: auto; }
            .hidden { display: none; }
            .font-serif { font-family: serif; }
            .font-sans { font-family: sans-serif; }
            .font-mono { font-family: monospace; }
        </style>
    </head>
    <body class="font-sans">

        <div id="drawer" class="fixed inset-y-0 right-0 w-64 bg-white shadow-2xl z-[150] transform translate-x-full transition-transform duration-300 dark:bg-gray-800">
            <div class="p-6">
                <h2 class="text-xl font-bold mb-6 border-b pb-2">תפריט</h2>
                <button onclick="setView('home')" class="w-full text-right py-3 flex items-center gap-2"><span class="material-icons">home</span> דף הבית</button>
                <div id="jobs-menu-list" class="mt-4 border-t pt-4"></div>
                <button onclick="openSettings()" class="w-full text-right py-3 mt-4 border-t flex items-center gap-2"><span class="material-icons">settings</span> הגדרות</button>
            </div>
        </div>
        <div id="overlay" class="fixed inset-0 bg-black opacity-50 z-[140] hidden" onclick="toggleDrawer()"></div>

        <header class="header p-4 shadow-md flex justify-between items-center sticky top-0 z-50">
            <span class="material-icons" onclick="toggleDrawer()">menu</span>
            <h1 id="view-title" class="text-lg font-bold">סקירה כללית</h1>
            <span class="material-icons" onclick="openShiftModal()">add</span>
        </header>

        <main class="p-4 pb-32">
            <section id="view-home">
                <div class="card p-6 mb-6 text-center border-t-4 border-cyan-500">
                    <p class="text-sm opacity-70">סה"כ הכנסות צפויות (חודש נוכחי)</p>
                    <p class="text-4xl font-black mt-2 text-cyan-600">₪ <span id="home-total-money">0.00</span></p>
                </div>
                <h3 class="font-bold mb-3 flex items-center gap-2"><span class="material-icons text-sm">history</span> תיעודים אחרונים</h3>
                <div id="global-history" class="space-y-3"></div>
            </section>

            <section id="view-job" class="hidden">
                <div id="job-shift-list" class="space-y-3"></div>
            </section>
        </main>

        <footer id="job-footer" class="fixed bottom-0 left-0 right-0 bg-cyan-500 text-white p-4 flex justify-around font-bold shadow-lg hidden">
            <div>שעות: <span id="job-total-hours">0.00</span></div>
            <div>סה"כ: ₪ <span id="job-total-pay">0.00</span></div>
        </footer>

        <div id="settingsModal" class="modal">
            <div class="modal-content">
                <h2 class="font-bold mb-4">הגדרות אפליקציה</h2>
                <div class="space-y-4">
                    <div>
                        <label class="block text-xs mb-1">מצב תצוגה</label>
                        <select onchange="setTheme(this.value)" class="w-full border p-2 rounded dark:bg-gray-700">
                            <option value="light">בהיר</option>
                            <option value="dark">כהה</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs mb-1">גודל טקסט</label>
                        <input type="range" min="14" max="22" value="16" oninput="setFontSize(this.value)" class="w-full">
                    </div>
                    <div>
                        <label class="block text-xs mb-1">פונט</label>
                        <select onchange="setFontFamily(this.value)" class="w-full border p-2 rounded dark:bg-gray-700">
                            <option value="font-sans">Sans Serif (מודרני)</option>
                            <option value="font-serif">Serif (קלאסי)</option>
                            <option value="font-mono">Monospace (טכני)</option>
                        </select>
                    </div>
                    <button onclick="openJobsManager()" class="w-full bg-cyan-600 text-white py-2 rounded">ניהול מקומות עבודה</button>
                </div>
                <button onclick="closeModal('settingsModal')" class="w-full mt-6 text-gray-400">סגור</button>
            </div>
        </div>

        <div id="shiftModal" class="modal"><div class="modal-content">... (קוד הוספת משמרת) ...</div></div>

        <script>
            let jobs = JSON.parse(localStorage.getItem('jobs')) || [];
            let shifts = JSON.parse(localStorage.getItem('shifts')) || [];
            let currentView = 'home';
            let currentJobId = null;

            window.onload = () => {
                applySettings();
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
                renderView();
                toggleDrawer();
            }

            function renderView() {
                document.getElementById('view-home').classList.toggle('hidden', currentView !== 'home');
                document.getElementById('view-job').classList.toggle('hidden', currentView !== 'job');
                document.getElementById('job-footer').classList.toggle('hidden', currentView !== 'job');

                if (currentView === 'home') {
                    document.getElementById('view-title').innerText = 'סקירה כללית';
                    renderHome();
                } else {
                    const job = jobs.find(j => j.id == currentJobId);
                    document.getElementById('view-title').innerText = job ? job.name : 'עבודה';
                    renderJobView();
                }
                renderJobsMenu();
            }

            function renderHome() {
                const total = shifts.reduce((acc, s) => acc + s.data.total_pay, 0);
                document.getElementById('home-total-money').innerText = total.toLocaleString();
                
                const history = [...shifts].sort((a,b) => new Date(b.start) - new Date(a.start)).slice(0, 10);
                document.getElementById('global-history').innerHTML = history.map(s => `
                    <div class="card p-3 flex justify-between items-center text-sm">
                        <span><strong>${s.jobName}</strong> | ${s.start.split('T')[0]}</span>
                        <span class="font-bold text-cyan-600">₪${s.data.total_pay}</span>
                    </div>
                `).join('');
            }

            function renderJobView() {
                const jobShifts = shifts.filter(s => s.jobId == currentJobId);
                const container = document.getElementById('job-shift-list');
                container.innerHTML = jobShifts.map((s, i) => `
                    <div class="card p-4 flex justify-between items-center">
                        <div><p class="text-xs opacity-60">${s.start.split('T')[0]}</p><p class="font-bold">${s.start.split('T')[1]} - ${s.end.split('T')[1]}</p></div>
                        <div class="text-right"><p class="text-xl font-bold text-cyan-600">₪${s.data.total_pay}</p></div>
                    </div>
                `).join('');

                document.getElementById('job-total-hours').innerText = jobShifts.reduce((acc, s) => acc + s.data.hours, 0).toFixed(2);
                document.getElementById('job-total-pay').innerText = jobShifts.reduce((acc, s) => acc + s.data.total_pay, 0).toLocaleString();
            }

            function renderJobsMenu() {
                const list = document.getElementById('jobs-menu-list');
                list.innerHTML = jobs.map(j => `
                    <button onclick="setView('job', ${j.id})" class="w-full text-right py-3 px-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2">
                        <span class="material-icons text-sm">circle</span> ${j.name}
                    </button>
                `).join('');
            }

            // פונקציות עיצוב
            function setTheme(theme) {
                document.body.classList.toggle('dark', theme === 'dark');
                localStorage.setItem('theme', theme);
            }
            function setFontSize(size) {
                document.documentElement.style.setProperty('--font-size', size + 'px');
                localStorage.setItem('font-size', size);
            }
            function setFontFamily(font) {
                document.body.className = font + (localStorage.getItem('theme') === 'dark' ? ' dark' : '');
                localStorage.setItem('font-family', font);
            }
            function applySettings() {
                setTheme(localStorage.getItem('theme'));
                setFontSize(localStorage.getItem('font-size') || 16);
                setFontFamily(localStorage.getItem('font-family') || 'font-sans');
            }

            function openSettings() { document.getElementById('settingsModal').style.display = 'flex'; toggleDrawer(); }
            function closeModal(id) { document.getElementById(id).style.display = 'none'; }
            
            // שאר הפונקציות (saveShift, calculate וכו') נשארות זהות מהקוד הקודם...
        </script>
    </body>
    </html>
    """
