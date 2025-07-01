from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import httpx
import os
from supabase_client import supabase
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

# ✅ WhatsApp Verification (GET)
@app.get("/whatsapp/webhook")
async def verify_token(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return PlainTextResponse(content=params.get("hub.challenge"), status_code=200)

    return PlainTextResponse(content="Verification failed", status_code=403)

# ✅ Incoming WhatsApp Message (POST)
@app.post("/whatsapp/webhook")
async def receive_whatsapp_message(request: Request):
    body = await request.json()
    print("📨 Incoming:", body)

    try:
        messages = body["entry"][0]["changes"][0]["value"].get("messages", [])
        if messages:
            msg = messages[0]
            user_number = msg["from"]
            text = msg["text"]["body"].strip().lower()

            print(f"From {user_number}: {text}")

            if text == "hi":
                await send_whatsapp_message(user_number, 
                    "Hi 👋, welcome to Fundibot! Type 'book' to find a fundi near you.")
            elif text == "book":
                await send_whatsapp_message(user_number, 
                    "Great! What type of fundi do you need? (e.g. plumber, electrician)")
            else:
                print("🔇 No reply sent (quota saved)")
    except Exception as e:
        print("❌ Error handling message:", e)

    return {"status": "received"}

# ✅ Function to Send WhatsApp Message via Cloud API
async def send_whatsapp_message(recipient: str, text: str):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": text}
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        print("✅ Sent reply:", response.status_code, response.text)


# ✅ Fundibot API Endpoints Below

@app.get("/ping")
def test_connection():
    response = supabase.table("users").select("*").limit(1).execute()
    return {"status": "connected", "data": response.data}

@app.post("/register_user/")
async def register_user(payload: dict):
    phone = payload.get("phone_number")
    name = payload.get("full_name")
    location = payload.get("location")

    existing = supabase.table("users").select("id").eq("phone_number", phone).execute()
    if existing.data:
        return {"message": "User already exists"}

    supabase.table("users").insert({
        "phone_number": phone,
        "full_name": name,
        "location": location
    }).execute()

    return {"message": "User registered"}

@app.post("/register_fundi/")
async def register_fundi(payload: dict):
    supabase.table("fundis").insert(payload).execute()
    return {"message": "Fundi registered. Awaiting approval."}

@app.get("/fundis/")
def find_fundis(skill: str, location: str):
    response = supabase.table("fundis")\
        .select("*")\
        .eq("skill", skill)\
        .eq("location", location)\
        .eq("is_approved", True)\
        .execute()
    return response.data

@app.post("/book/")
def create_booking(payload: dict):
    user_id = payload["user_id"]
    fundi_id = payload["fundi_id"]
    location = payload["location"]
    base_price = payload["base_price"]
    final_price = int(base_price * 1.10)

    supabase.table("bookings").insert({
        "user_id": user_id,
        "fundi_id": fundi_id,
        "location": location,
        "base_price": base_price,
        "final_price": final_price,
        "status": "pending"
    }).execute()

    return {"message": "Booking created", "final_price": final_price}
