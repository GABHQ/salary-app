from fastapi import FastAPI
from pydantic import BaseModel
import requests
from datetime import datetime, timedelta
from dateutil import parser
import pytz

app = FastAPI()

# הגדרות מיקום (ישראל)
TIMEZONE = pytz.timezone('Asia/Jerusalem')

class ShiftRequest(BaseModel):
    start_time: str
    end_time: str
    base_rate: float

def get_holidays(year):
    # API של חגי ישראל (HebCal)
    url = f"https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&min=on&mod=on&nx=on&year={year}&month=all&ss=on&mf=on&c=on"
    return requests.get(url).json().get('items', [])

@app.get("/api/health")
def health():
    return {"status": "alive"}

@app.post("/api/calculate")
async def calculate(shift: ShiftRequest):
    start = parser.isoparse(shift.start_time).astimezone(TIMEZONE)
    end = parser.isoparse(shift.end_time).astimezone(TIMEZONE)
    holidays = get_holidays(start.year)
    
    total_pay = 0
    current_time = start
    delta = timedelta(minutes=15)
    
    while current_time < end:
        multiplier = 1.0
        # שבת: משישי ב-18:00 עד מוצ"ש ב-20:00 (הערכה ל-MVP)
        if (current_time.weekday() == 4 and current_time.hour >= 18) or \
           (current_time.weekday() == 5 and current_time.hour < 20):
            multiplier = 1.5
            
        # בדיקת חגים
        date_str = current_time.strftime('%Y-%m-%d')
        for h in holidays:
            if h.get('date') == date_str:
                multiplier = 1.5 if "Erev" in h.get('title', '') else 2.0
                break

        total_pay += (shift.base_rate * multiplier) * (15 / 60)
        current_time += delta

    return {"total_pay": round(total_pay, 2), "hours": (end - start).total_seconds() / 3600}
