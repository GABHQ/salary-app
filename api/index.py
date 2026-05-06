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
        <title>ניהול שכר - עבודות מרובות</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            .header { background-color: #00acc1; color: white; }
            .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); align-items: flex-end; z-index: 50; }
            .modal-content { background: white; width: 100%; border-radius: 20px 20px 0 0; padding: 20px; max-height: 90vh; overflow-y: auto; }
            .info-icon { font-size: 16px; color: #00acc1; cursor: pointer; vertical-align: middle; margin-right: 4px; }
            .mandatory { color: red; margin-right: 2px; }
        </style>
    </head>
    <body class="bg-gray-100 font-sans min-h-screen">
        <header class="header p-4 shadow-md flex justify-between items-center">
            <span class="material-icons" onclick="openJobsModal()">work</span>
            <h1 id="current-month" class="text-xl font-bold">ניהול שכר 2026</h1>
            <span class="material-icons">settings</span>
        </header>

        <main id="shift-container" class="p-4 space-y-3 pb-32"></main>

        <div id="jobsModal" class="modal">
            <div class="modal-content">
                <h2 class="font-bold border-b pb-2 mb-4">ניהול מקומות עבודה</h2>
                <div id="jobs-list" class="mb-4 space-y-2"></div>
                <button onclick="showAddJobForm()" class="w-full bg-cyan-600 text-white py-2 rounded mb-4">+ עבודה חדשה</button>
                
                <div id="job-form" class="hidden border-t pt-4">
                    <div class="mb-2"><label><span class="mandatory">*</span>שם עבודה:</label> <input id="j_name" class="w-full border p-2 rounded"></div>
                    <div class="mb-2"><label><span class="mandatory">*</span>סוג שכר:</label> 
                        <select id="j_type" onchange="toggleJobFields()" class="w-full border p-2 rounded">
                            <option value="hourly">שעתי</option>
                            <option value="monthly">גלובלי / חודשי</option>
                        </select>
                    </div>
                    <div id="hourly_fields" class="mb-2">
                        <label><span class="mandatory">*</span>שכר שעתי:</label> <input type="number" id="j_rate" class="w-full border p-2 rounded">
                    </div>
                    <div id="monthly_fields" class="hidden mb-2">
                        <label><span class="mandatory">*</span>שכר חודשי:</label> <input type="number" id="j_monthly" class="w-full border p-2 rounded">
                    </div>
                    <button onclick="saveJob()" class="w-full bg-green-600 text-white py-2 rounded">שמור עבודה</button>
                </div>
                <button onclick="closeModal('jobsModal')" class="w-full mt-2 text-gray-500">סגור</button>
            </div>
        </div>

        <div id="shiftModal" class="modal">
            <div class="modal-content">
                <h2 class="text-center font-bold text-cyan-700 mb-4 border-b pb-2">הוספת משמרת</h2>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div class="col-span-2">
                        <label><span class="mandatory">*</span>בחר עבודה:</label>
                        <select id="s_job" class="w-full border p-2 rounded"></select>
                    </div>
                    <div><label><span class="mandatory">*</span>תאריך:</label><input type="date" id="s_date" class="w-full border p-2 rounded"></div>
                    <div><label><span class="mandatory">*</span>כניסה:</label><input type="time" id="s_start" class="w-full border p-2 rounded"></div>
                    <div><label><span class="mandatory">*</span>יציאה:</label><input type="time" id="s_end" class="w-full border p-2 rounded"></div>
                    <div>
                        <label>הפסקה (דק'): <i class="material-icons info-icon" onclick="alert('זמן שיקוזז מהשעות הכוללות (למשל 30 דקות הפסקת אוכל)')">info</i></label>
                        <input type="number" id="s_break" value="0" class="w-full border p-2 rounded">
                    </div>
                    <div>
                        <label>תוספת (₪): <i class="material-icons info-icon" onclick="alert('בונוס חד פעמי למשמרת הזו (טיפים, נסיעות וכו\')')">info</i></label>
                        <input type="number" id="s_extra" value="0" class="w-full border p-2 rounded">
                    </div>
                </div>
                <div class="flex gap-2 mt-6">
                    <button onclick="saveShift()" class="flex-1 bg-cyan-600 text-white py-3 rounded-lg font-bold">שמור משמרת</button>
                    <button onclick="closeModal('shiftModal')" class="flex-1 bg-gray-200 py-3 rounded-lg font-bold">ביטול</button>
                </div>
            </div>
        </div>

        <footer class="fixed bottom-0 left-0 right-0 bg-[#4dd0e1] text-white p-3 flex justify-around text-sm font-bold shadow-lg">
            <div>שעות: <span id="total-hours">0.00</span></div>
            <div>סה"כ: ₪ <span id="total-money">0.00</span></div>
        </footer>

        <div class="fixed bottom-24 right-6 flex flex-col gap-4">
            <div onclick="openShiftModal()" class="w-14 h-14 bg-[#e91e63] rounded-full flex items-center justify-center text-white shadow-lg"><span class="material-icons">add</span></div>
        </div>

        <script>
            let jobs = JSON.parse(localStorage.getItem('jobs')) || [];
            let shifts = JSON.parse(localStorage.getItem('shifts')) || [];

            window.onload = () => {
                document.getElementById('s_date').value = new Date().toISOString().split('T')[0];
                renderShifts();
                updateJobSelect();
            };

            function openJobsModal() { document.getElementById('jobsModal').style.display = 'flex'; renderJobs(); }
            function openShiftModal() { 
                if(jobs.length === 0) return alert('קודם כל תגדיר עבודה בתפריט העבודות (צד ימין למעלה)');
                document.getElementById('shiftModal').style.display = 'flex'; 
            }
            function closeModal(id) { document.getElementById(id).style.display = 'none'; }
            function showAddJobForm() { document.getElementById('job-form').classList.toggle('hidden'); }
            
            function toggleJobFields() {
                const type = document.getElementById('j_type').value;
                document.getElementById('hourly_fields').classList.toggle('hidden', type !== 'hourly');
                document.getElementById('monthly_fields').classList.toggle('hidden', type !== 'monthly');
            }

            function saveJob() {
                const job = {
                    id: Date.now(),
                    name: document.getElementById('j_name').value,
                    type: document.getElementById('j_type').value,
                    rate: parseFloat(document.getElementById('j_rate').value) || 0,
                    monthly: parseFloat(document.getElementById('j_monthly').value) || 0
                };
                if(!job.name) return alert('חובה להזין שם עבודה');
                jobs.push(job);
                localStorage.setItem('jobs', JSON.stringify(jobs));
                renderJobs();
                updateJobSelect();
                document.getElementById('job-form').classList.add('hidden');
            }

            function renderJobs() {
                const list = document.getElementById('jobs-list');
                list.innerHTML = jobs.map(j => `<div class="p-2 bg-gray-50 rounded border flex justify-between">
                    <span>${j.name} (${j.type === 'hourly' ? j.rate + '₪' : 'גלובלי'})</span>
                    <span class="text-red-500 material-icons" style="font-size:18px" onclick="deleteJob(${j.id})">delete</span>
                </div>`).join('');
            }

            function deleteJob(id) { jobs = jobs.filter(j => j.id !== id); localStorage.setItem('jobs', JSON.stringify(jobs)); renderJobs(); updateJobSelect(); }

            function updateJobSelect() {
                const select = document.getElementById('s_job');
                select.innerHTML = jobs.map(j => `<option value="${j.id}">${j.name}</option>`).join('');
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
                        start_time: start, 
                        end_time: end, 
                        base_rate: job.type === 'hourly' ? job.rate : (job.monthly / 186), // הערכה גסה לשעה בגלובלי
                        break_mins: parseInt(document.getElementById('s_break').value) || 0,
                        extra_pay: parseFloat(document.getElementById('s_extra').value) || 0
                    })
                });
                const data = await res.json();
                shifts.push({ jobId, jobName: job.name, start, end, data });
                localStorage.setItem('shifts', JSON.stringify(shifts));
                renderShifts();
                closeModal('shiftModal');
            }

            function renderShifts() {
                const container = document.getElementById('shift-container');
                container.innerHTML = shifts.map((s, i) => `
                    <div class="bg-white p-4 rounded-lg shadow-sm border-r-4 border-cyan-600 flex justify-between items-center mb-2">
                        <div>
                            <p class="text-[10px] text-cyan-600 font-bold uppercase">${s.jobName}</p>
                            <p class="text-xs text-gray-500">${s.start.split('T')[0]}</p>
                            <p class="font-bold">${s.start.split('T')[1]} - ${s.end.split('T')[1]}</p>
                        </div>
                        <div class="text-right">
                            <p class="text-xl font-bold text-cyan-700">₪ ${s.data.total_pay}</p>
                            <button onclick="deleteShift(${i})" class="text-gray-300 material-icons" style="font-size:16px">delete</button>
                        </div>
                    </div>
                `).join('');
                updateTotals();
            }

            function deleteShift(i) { shifts.splice(i, 1); localStorage.setItem('shifts', JSON.stringify(shifts)); renderShifts(); }
            function updateTotals() {
                document.getElementById('total-hours').innerText = shifts.reduce((acc, s) => acc + s.data.hours, 0).toFixed(2);
                document.getElementById('total-money').innerText = shifts.reduce((acc, s) => acc + s.data.total_pay, 0).toFixed(2);
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
    
    break_deduction = (shift.break_mins / 60) * shift.base_rate
    final_pay = round(total_pay - break_deduction + shift.extra_pay, 2)
    return {"total_pay": max(0, final_pay), "hours": (end - start).total_seconds() / 3600}
