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
        <title>Smart Salary Pro 2026</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            :root { --bg: #ffffff; --card: #f9fafb; --text: #111827; --accent: #00acc1; }
            body.dark { --bg: #111827; --card: #1f2937; --text: #f9fafb; --accent: #26c6da; }
            body { background-color: var(--bg); color: var(--text); transition: 0.3s; margin: 0; padding-bottom: 80px; }
            .card { background-color: var(--card); border-radius: 16px; border: 1px solid rgba(0,0,0,0.05); }
            .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); align-items: flex-end; z-index: 500; }
            .modal-content { background: var(--bg); border-radius: 24px 24px 0 0; padding: 24px; width: 100%; max-height: 90vh; overflow-y: auto; }
            .info-i { font-size: 14px; color: var(--accent); cursor: pointer; margin-right: 4px; }
            .bottom-nav { position: fixed; bottom: 0; left: 0; right: 0; background: var(--bg); height: 70px; display: flex; justify-content: space-around; align-items: center; border-top: 1px solid rgba(0,0,0,0.1); z-index: 400; }
            .nav-item { opacity: 0.4; transition: 0.2s; text-align: center; }
            .nav-item.active { opacity: 1; color: var(--accent); }
            input, select, textarea { background: var(--card) !important; color: var(--text) !important; border: 1px solid rgba(0,0,0,0.1) !important; width: 100%; padding: 12px; border-radius: 12px; }
        </style>
    </head>
    <body class="font-sans">

        <header class="bg-cyan-600 text-white p-4 shadow-md flex justify-between items-center sticky top-0 z-50">
            <h1 id="view-title" class="text-lg font-bold">טוען...</h1>
            <span class="material-icons cursor-pointer" onclick="openShiftModal()">add_circle</span>
        </header>

        <main id="main-content" class="p-4">
            </main>

        <nav class="bottom-nav">
            <div class="nav-item" onclick="setView('home')" id="nav-home"><span class="material-icons">dashboard</span><p class="text-[10px]">ראשי</p></div>
            <div class="nav-item" onclick="setView('jobs')" id="nav-jobs"><span class="material-icons">work</span><p class="text-[10px]">עבודות</p></div>
            <div class="nav-item" id="nav-stats"><span class="material-icons">analytics</span><p class="text-[10px]">ניתוח</p></div>
            <div class="nav-item" onclick="openSettings()" id="nav-settings"><span class="material-icons">settings</span><p class="text-[10px]">הגדרות</p></div>
        </nav>

        <div id="settingsModal" class="modal" onclick="if(event.target==this)closeAll()">
            <div class="modal-content">
                <h2 class="font-bold mb-4 border-b pb-2">ניהול עבודות והגדרות</h2>
                <div id="jobs-manager-list" class="space-y-2 mb-6"></div>
                <div class="card p-4">
                    <p class="font-bold text-xs mb-3 opacity-50 uppercase">הוספת עבודה</p>
                    <div class="space-y-3">
                        <input id="j_name" placeholder="שם העבודה">
                        <div class="grid grid-cols-2 gap-2">
                            <input id="j_rate" type="number" placeholder="שכר שעתי">
                            <select id="j_culture"><option value="jewish">יהודי (חגים/שבת)</option><option value="muslim">מוסלמי</option></select>
                        </div>
                        <div class="text-[10px] space-y-1 opacity-70">
                            <p>125% אחרי: <input id="j_ot1" type="number" value="8.5" class="w-12 p-1 inline"> שעות <i class="material-icons info-i" onclick="showInfo('ot')">info</i></p>
                            <p>150% אחרי: <input id="j_ot2" type="number" value="10.5" class="w-12 p-1 inline"> שעות</p>
                        </div>
                        <button onclick="saveJob()" class="w-full bg-cyan-600 text-white py-3 rounded-xl font-bold">שמור עבודה</button>
                    </div>
                </div>
                <button onclick="closeAll()" class="w-full mt-6 py-4 bg-gray-100 rounded-xl font-bold dark:bg-gray-800">סגור</button>
            </div>
        </div>

        <div id="shiftModal" class="modal" onclick="if(event.target==this)closeAll()">
            <div class="modal-content">
                <h2 class="font-bold mb-4 text-center text-cyan-600">תיעוד משמרת</h2>
                <div class="space-y-4">
                    <div id="job-selector-container">
                        <label class="text-[10px] opacity-50">עבודה:</label>
                        <select id="s_job"></select>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="date" id="s_date">
                        <div class="flex gap-2">
                            <input type="time" id="s_start">
                            <input type="time" id="s_end">
                        </div>
                    </div>
                    <div class="grid grid-cols-2 gap-3">
                        <input type="number" id="s_break" placeholder="הפסקה (דק')">
                        <input type="number" id="s_extra" placeholder="בונוס/טיפ">
                    </div>
                    <textarea id="s_notes" placeholder="הערות למשמרת (למשל: 'היה עומס מטורף', 'סגירת קופה')" rows="2"></textarea>
                    <button onclick="saveShift()" class="w-full bg-cyan-600 text-white py-4 rounded-xl font-bold shadow-lg">שמור</button>
                </div>
            </div>
        </div>

        <script>
            let jobs = JSON.parse(localStorage.getItem('jobs')) || [];
            let shifts = JSON.parse(localStorage.getItem('shifts')) || [];
            let currentView = localStorage.getItem('lastView') || 'home';
            let currentJobId = localStorage.getItem('lastJobId') || null;

            window.onload = () => {
                applyTheme();
                renderView();
            };

            function showInfo(type) {
                const info = {
                    ot: "לפי חוק שעות עבודה ומנוחה: משמרת רגילה היא 8.4 שעות (במשרה של 5 ימים). השעתיים הראשונות מעבר לכך מזכות ב-125%, וכל שעה נוספת ב-150%. מקור: כל-זכות."
                };
                alert(info[type]);
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
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                
                if (currentView === 'home') {
                    document.getElementById('nav-home').classList.add('active');
                    document.getElementById('view-title').innerText = 'סקירה כללית';
                    renderHome(main);
                } else if (currentView === 'jobs') {
                    document.getElementById('nav-jobs').classList.add('active');
                    document.getElementById('view-title').innerText = 'העבודות שלי';
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
                const totalNet = totalGross * 0.90; // הערכה גסה לנטו (ביטוח לאומי + בריאות)
                container.innerHTML = `
                    <div class="card p-8 mb-6 text-center border-t-4 border-cyan-500">
                        <p class="text-[10px] uppercase font-bold opacity-50">ברוטו חודשי</p>
                        <p class="text-4xl font-black text-cyan-600">₪${totalGross.toLocaleString()}</p>
                        <p class="text-xs mt-2 opacity-60 italic">נטו משוער: ₪${totalNet.toLocaleString()}</p>
                    </div>
                    <h3 class="font-bold mb-4 text-sm opacity-70">10 משמרות אחרונות</h3>
                    <div class="space-y-3">
                        ${shifts.sort((a,b) => new Date(b.start) - new Date(a.start)).slice(0,10).map(s => `
                            <div class="card p-4 flex justify-between items-center" onclick="alert('הערות: ${s.notes || "אין"}')">
                                <div><p class="text-[9px] font-bold text-cyan-600 uppercase">${s.jobName}</p><p class="text-xs opacity-50">${s.start.split('T')[0]}</p></div>
                                <div class="font-bold">₪${s.data.total_pay}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            function renderJobsList(container) {
                container.innerHTML = jobs.map(j => `
                    <div class="card p-5 mb-3 flex justify-between items-center" onclick="setView('job', ${j.id})">
                        <span class="font-bold text-lg">${j.name} • <span class="text-xs opacity-50">${j.rate}₪</span></span>
                        <span class="material-icons opacity-30">chevron_left</span>
                    </div>
                `).join('');
            }

            function renderJobDetails(container, job) {
                const jobShifts = shifts.filter(s => s.jobId == job.id).sort((a,b) => new Date(b.start) - new Date(a.start));
                const totalHours = jobShifts.reduce((acc, s) => acc + s.data.hours, 0);
                const totalPay = jobShifts.reduce((acc, s) => acc + s.data.total_pay, 0);
                
                container.innerHTML = `
                    <div class="space-y-3">
                        ${jobShifts.map(s => `
                            <div class="card p-4 flex justify-between items-center" onclick="alert('סיכום משמרת:\\nשעות: ${s.data.hours.toFixed(2)}\\nהערות: ${s.notes || "אין"}')">
                                <div><p class="text-xs opacity-40">${s.start.split('T')[0]}</p><p class="font-bold text-sm">${s.start.split('T')[1]} - ${s.end.split('T')[1]}</p></div>
                                <div class="text-right"><p class="text-lg font-black text-cyan-600">₪${s.data.total_pay}</p></div>
                            </div>
                        `).join('')}
                    </div>
                    <footer class="fixed bottom-[70px] left-0 right-0 bg-cyan-700 text-white p-4 flex justify-around font-bold">
                        <div class="text-center"><p class="text-[9px] opacity-70">שעות</p>${totalHours.toFixed(2)}</div>
                        <div class="text-center"><p class="text-[9px] opacity-70">שכר</p>₪${totalPay.toLocaleString()}</div>
                    </footer>
                `;
            }

            function openShiftModal() {
                if(jobs.length === 0) return alert('הוסף עבודה בהגדרות קודם');
                
                // הוספת עבודה אוטומטית לפי ההקשר
                const selector = document.getElementById('job-selector-container');
                const select = document.getElementById('s_job');
                select.innerHTML = jobs.map(j => `<option value="${j.id}">${j.name}</option>`).join('');
                
                if (currentView === 'job' && currentJobId) {
                    select.value = currentJobId;
                    selector.classList.add('hidden'); // אל תשאל שוב אם אני כבר בתוך העבודה
                } else {
                    selector.classList.remove('hidden');
                }
                
                document.getElementById('s_date').value = new Date().toISOString().split('T')[0];
                document.getElementById('shiftModal').style.display = 'flex';
            }

            function saveJob() {
                const name = document.getElementById('j_name').value;
                const rate = document.getElementById('j_rate').value;
                if(!name || !rate) return;
                jobs.push({ 
                    id: Date.now(), name, rate: parseFloat(rate), 
                    ot1: parseFloat(document.getElementById('j_ot1').value),
                    ot2: parseFloat(document.getElementById('j_ot2').value),
                    culture: document.getElementById('j_culture').value
                });
                localStorage.setItem('jobs', JSON.stringify(jobs));
                closeAll();
                renderView();
            }

            async function saveShift() {
                const jobId = document.getElementById('s_job').value;
                const job = jobs.find(j => j.id == jobId);
                const start = document.getElementById('s_date').value + 'T' + document.getElementById('s_start').value;
                const end = document.getElementById('s_date').value + 'T' + document.getElementById('s_end').value;

                try {
                    const res = await fetch('/api/calculate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            start_time: start, end_time: end, base_rate: job.rate,
                            break_mins: parseInt(document.getElementById('s_break').value || 0),
                            extra_pay: parseFloat(document.getElementById('s_extra').value || 0),
                            overtime_125_after: job.ot1, overtime_150_after: job.ot2
                        })
                    });
                    const data = await res.json();
                    shifts.push({ 
                        id: Date.now(), jobId, jobName: job.name, start, end, data, 
                        notes: document.getElementById('s_notes').value 
                    });
                    localStorage.setItem('shifts', JSON.stringify(shifts));
                    closeAll();
                    renderView();
                } catch(e) { alert('שגיאה בחישוב'); }
            }

            function closeAll() { document.querySelectorAll('.modal').forEach(m => m.style.display='none'); }
            function openSettings() { renderJobsManager(); document.getElementById('settingsModal').style.display = 'flex'; }
            function renderJobsManager() {
                document.getElementById('jobs-manager-list').innerHTML = jobs.map(j => `<div class="card p-3 flex justify-between items-center mb-2"><span class="text-sm font-bold">${j.name}</span><span class="material-icons text-red-400 text-sm cursor-pointer" onclick="deleteJob(${j.id})">delete</span></div>`).join('');
            }
            function deleteJob(id) { jobs = jobs.filter(j => j.id != id); localStorage.setItem('jobs', JSON.stringify(jobs)); renderJobsManager(); renderView(); }
            function applyTheme() { if(localStorage.getItem('theme')==='dark') document.body.classList.add('dark'); }
            function setTheme(t) { document.body.classList.toggle('dark', t==='dark'); localStorage.setItem('theme', t); }
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
    
    # חישוב משך משמרת ברוטו בשעות
    duration_hours = (end - start).total_seconds() / 3600
    actual_work_hours = duration_hours - (shift.break_mins / 60)
    
    while curr < end:
        # בדיקת חג/שבת
        mult = 1.0
        if (curr.weekday() == 4 and curr.hour >= 18) or (curr.weekday() == 5 and curr.hour < 20):
            mult = 1.5
        for h in holidays:
            if h.get('date') == curr.strftime('%Y-%m-%d'):
                mult = shift.holiday_rate
                break
        
        # חישוב שעות נוספות לפי זמן יחסי במשמרת
        elapsed_hours = (curr - start).total_seconds() / 3600
        if elapsed_hours >= shift.overtime_150_after:
            mult = max(mult, 1.5)
        elif elapsed_hours >= shift.overtime_125_after:
            mult = max(mult, 1.25)
            
        total_pay += (shift.base_rate * mult) * (15/60)
        curr += step

    # קיזוז הפסקה לפי שכר בסיס
    deduction = (shift.break_mins / 60) * shift.base_rate
    final_pay = round(total_pay - deduction + shift.extra_pay, 2)
    
    return {"total_pay": max(0, final_pay), "hours": actual_work_hours}
