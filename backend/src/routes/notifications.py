from fastapi import APIRouter
from pydantic import BaseModel
import os

router = APIRouter()

class WhatsAppRequest(BaseModel):
    phone: str
    message: str

class EmailRequest(BaseModel):
    email: str
    subject: str
    body: str

@router.post("/test-whatsapp")
def test_whatsapp(req: WhatsAppRequest):
    try:
        from twilio.rest import Client
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        if not sid or not token:
            return {"status": "error", "detail": "Twilio credentials missing"}
            
        client = Client(sid, token)
        client.messages.create(
            from_='whatsapp:+14155238886',
            to=f'whatsapp:+{req.phone}' if not req.phone.startswith('+') else f'whatsapp:{req.phone}',
            body=req.message
        )
        return {"status": "sent"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.post("/test-email")
def test_email(req: EmailRequest):
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            return {"status": "error", "detail": "SendGrid API key missing"}
            
        sg = sendgrid.SendGridAPIClient(api_key)
        mail = Mail(
            from_email="urjadrishti@kredl.karnataka.gov.in",
            to_emails=req.email,
            subject=req.subject,
            html_content=req.body
        )
        sg.send(mail)
        return {"status": "sent"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
