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
        return requests.get(url).json().get('items', [])
    except: return []

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    return """
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>מחשבון שכר</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            .header { background-color: #00acc1; color: white; }
            .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); align-items: flex-end; z-index: 50; }
            .modal-content { background: white; width: 100%; border-radius: 20px 20px 0 0; padding: 20px; animation: slideUp 0.3s ease-out; }
            @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
            .input-group { margin-bottom: 15px; }
            .input-group label { display: block; font-size: 12px; color: #666; margin-bottom: 4px; }
            .input-group input { width: 100%; border: 1px solid #ddd; padding: 8px; border-radius: 8px; }
            .fab-menu { position: fixed; bottom: 24px; right: 24px; display: flex; flex-direction: column; align-items: flex-end; gap: 10px; }
            .btn-circle { width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.3); cursor: pointer; }
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen font-sans">
        <header class="header p-4 shadow-md flex justify-between items-center">
            <span class="material-icons">menu</span>
            <h1 class="text-xl font-bold">מאי 2026</h1>
            <span class="material-icons">wb_incandescent</span>
        </header>

        <main id="shift-container" class="p-4 space-y-3 pb-32"></main>

        <div id="shiftModal" class="modal" onclick="if(event.target==this)closeModal()">
            <div class="modal-content">
                <h2 class="text-center font-bold text-cyan-700 mb-4 border-b pb-2">פרטי משמרת</h2>
                <div class="grid grid-cols-2 gap-4 text-sm">
                    <div class="input-group"><label>תאריך:</label><input type="date" id="m_date"></div>
                    <div class="input-group"><label>שכר בסיס:</label><input type="number" id="m_rate" value="50"></div>
                    <div class="input-group"><label>כניסה:</label><input type="time" id="m_start"></div>
                    <div class="input-group"><label>יציאה:</label><input type="time" id="m_end"></div>
                    <div class="input-group"><label>הפסקה (דק'):</label><input type="number" id="m_break" value="0"></div>
                    <div class="input-group"><label>תוספת (₪):</label><input type="number" id="m_extra" value="0"></div>
                </div>
                <div class="flex gap-2 mt-4">
                    <button onclick="saveShift()" class="flex-1 bg-cyan-600 text-white py-3 rounded-lg font-bold">הוסף</button>
                    <button onclick="closeModal()" class="flex-1 bg-gray-200 py-3 rounded-lg font-bold">ביטול</button>
                </div>
            </div>
        </div>

        <footer class="fixed bottom-0 left-0 right-0 bg-[#4dd0e1] text-white p-3 flex justify-around text-sm font-bold">
            <div>שעות: <span id="total-hours">0.00</span></div>
            <div>סה"כ: ₪ <span id="total-money">0.00</span></div>
        </footer>

        <div class="fab-menu">
            <div onclick="openModal()" class="btn-circle bg-[#e91e63]"><span class="material-icons">add</span></div>
        </div>

        <script>
            let shifts = JSON.parse(localStorage.getItem('my_shifts')) || [];
            window.onload = () => { 
                const today = new Date().toISOString().split('T')[0];
                document.getElementById('m_date').value = today;
                renderAll(); 
            };

            function openModal() { document.getElementById('shiftModal').style.display = 'flex'; }
            function closeModal() { document.getElementById('shiftModal').style.display = 'none'; }

            async function saveShift() {
                const date = document.getElementById('m_date').value;
                const start = date + 'T' + document.getElementById('m_start').value;
                const end = date + 'T' + document.getElementById('m_end').value;
                const rate = document.getElementById('m_rate').value;
                const brk = document.getElementById('m_break').value;
                const extra = document.getElementById('m_extra').value;

                const res = await fetch('/api/calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ start_time: start, end_time: end, base_rate: parseFloat(rate), break_mins: parseInt(brk), extra_pay: parseFloat(extra) })
                });
                const data = await res.json();
                shifts.push({ date, start, end, data });
                localStorage.setItem('my_shifts', JSON.stringify(shifts));
                renderAll();
                closeModal();
            }

            function renderAll() {
                const container = document.getElementById('shift-container');
                container.innerHTML = '';
                shifts.forEach((s, index) => {
                    container.innerHTML += `
                    <div class="bg-white p-4 rounded-lg shadow-sm border-r-4 border-cyan-600 flex justify-between items-center mb-3">
                        <div>
                            <p class="text-xs text-gray-500">${s.date}</p>
                            <p class="font-bold">${s.start.split('T')[1]} - ${s.end.split('T')[1]}</p>
                        </div>
                        <div class="text-xl font-bold text-cyan-600">₪ ${s.data.total_pay}</div>
                        <button onclick="deleteShift(${index})" class="text-red-300"><span class="material-icons">delete</span></button>
                    </div>`;
                });
                updateTotals();
            }

            function deleteShift(i) {
                shifts.splice(i, 1);
                localStorage.setItem('my_shifts', JSON.stringify(shifts));
                renderAll();
            }

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
    if end < start: end += timedelta(days=1) # טיפול במשמרות לילה
    
    holidays = get_holidays(start.year)
    total_pay = 0
    curr = start
    step = timedelta(minutes=15)
    
    while curr < end:
        mult = 1.0
        # שבת
        if (curr.weekday() == 4 and curr.hour >= 18) or (curr.weekday() == 5 and curr.hour < 20):
            mult = 1.5
        # חג
        for h in holidays:
            if h.get('date') == curr.strftime('%Y-%m-%d'):
                mult = 1.5 if "Erev" in h.get('title', '') else 2.0
                break
        
        total_pay += (shift.base_rate * mult) * (15/60)
        curr += step
    
    # ניכוי הפסקה יחסי (לפי שכר בסיס)
    break_deduction = (shift.break_mins / 60) * shift.base_rate
    final_pay = round(total_pay - break_deduction + shift.extra_pay, 2)
    
    return {"total_pay": max(0, final_pay), "hours": (end - start).total_seconds() / 3600}
