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

def get_holidays(year):
    url = f"https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&min=on&mod=on&nx=on&year={year}&month=all&ss=on&mf=on&c=on"
    try:
        return requests.get(url).json().get('items', [])
    except:
        return []

# --- הוספת דף הבית ישירות לקוד ---
@app.get("/", response_class=HTMLResponse)
async def serve_home():
    return """
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>מחשבון שכר 2026</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
        <style>
            .header { background-color: #00acc1; color: white; }
            .fab { position: fixed; bottom: 24px; right: 24px; background-color: #e91e63; width: 64px; height: 64px; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.4); cursor: pointer; }
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen">
        <header class="header p-4 shadow-md flex justify-between items-center">
            <span class="material-icons">menu</span>
            <h1 class="text-xl font-bold">מאי 2026</h1>
            <span class="material-icons">wb_incandescent</span>
        </header>
        <main id="shift-container" class="p-4 space-y-3 pb-24"></main>
        <footer class="fixed bottom-0 left-0 right-0 bg-[#4dd0e1] text-white p-3 flex justify-around text-center text-sm font-bold shadow-lg">
            <div><p>שעות: <span id="total-hours">0.00</span></p></div>
            <div><p>סה"כ: ₪ <span id="total-money">0.00</span></p></div>
        </footer>
        <div class="fab text-white" onclick="triggerShiftDialog()"><span class="material-icons text-3xl">add</span></div>
        <script>
            let shifts = JSON.parse(localStorage.getItem('my_shifts')) || [];
            window.onload = () => { shifts.forEach(s => renderShift(s.start, s.end, s.data)); updateTotals(); };
            async function triggerShiftDialog() {
                const start = prompt("התחלה (YYYY-MM-DD HH:mm)", "2026-05-06 20:00");
                const end = prompt("סיום (YYYY-MM-DD HH:mm)", "2026-05-07 02:00");
                const rate = prompt("בסיס לשעה", "50");
                if (!start || !end || !rate) return;
                try {
                    const res = await fetch('/api/calculate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ start_time: start.replace(" ", "T"), end_time: end.replace(" ", "T"), base_rate: parseFloat(rate) })
                    });
                    const data = await res.json();
                    shifts.push({ start, end, data });
                    localStorage.setItem('my_shifts', JSON.stringify(shifts));
                    renderShift(start, end, data);
                    updateTotals();
                } catch (e) { alert("שגיאה: " + e.message); }
            }
            function renderShift(start, end, data) {
                const html = `<div class="bg-white p-4 rounded-lg shadow-sm border-r-4 border-cyan-600 flex justify-between items-center mb-3">
                    <div><p class="text-xs text-gray-500">${new Date(start).toLocaleDateString('he-IL')}</p><p class="font-bold">${start.split(" ")[1]} - ${end.split(" ")[1]}</p></div>
                    <div class="text-xl font-bold text-cyan-600">₪ ${data.total_pay}</div>
                </div>`;
                document.getElementById('shift-container').insertAdjacentHTML('afterbegin', html);
            }
            function updateTotals() {
                document.getElementById('total-hours').innerText = shifts.reduce((acc, s) => acc + s.data.hours, 0).toFixed(2);
                document.getElementById('total-money').innerText = shifts.reduce((acc, s) => acc + s.data.total_pay, 0).toFixed(2);
            }
        </script>
    </body>
    </html>
    """

@app.get("/api/health")
def health():
    return {"status": "alive"}

@app.post("/api/calculate")
async def calculate(shift: ShiftRequest):
    start = parser.isoparse(shift.start_time).astimezone(TIMEZONE)
    end = parser.isoparse(shift.end_time).astimezone(TIMEZONE)
    holidays = get_holidays(start.year)
    total_pay = 0
    curr = start
    step = timedelta(minutes=15)
    while curr < end:
        mult = 1.0
        if (curr.weekday() == 4 and curr.hour >= 18) or (curr.weekday() == 5 and curr.hour < 20):
            mult = 1.5
        d_str = curr.strftime('%Y-%m-%d')
        for h in holidays:
            if h.get('date') == d_str:
                mult = 1.5 if "Erev" in h.get('title', '') else 2.0
                break
        total_pay += (shift.base_rate * mult) * (15/60)
        curr += step
    return {"total_pay": round(total_pay, 2), "hours": (end - start).total_seconds() / 3600}
