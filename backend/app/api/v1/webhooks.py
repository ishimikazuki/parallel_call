"""Twilio webhook endpoints."""

from fastapi import APIRouter, Form, Response

router = APIRouter(prefix="/webhooks/twilio", tags=["webhooks"])


def twiml_response(content: str) -> Response:
    """Create a TwiML XML response."""
    return Response(
        content=content,
        media_type="application/xml",
    )


@router.post("/status")
async def call_status_webhook(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
    From: str = Form(None),
    To: str = Form(None),
    CallDuration: str = Form(None),
    ErrorCode: str = Form(None),
    ErrorMessage: str = Form(None),
) -> Response:
    """
    Handle Twilio call status updates.

    Called when call status changes:
    - initiated: Call is being placed
    - ringing: Phone is ringing
    - in-progress: Call is connected
    - completed: Call ended normally
    - busy: Line was busy
    - no-answer: No answer
    - failed: Call failed
    - canceled: Call was canceled
    """
    # Log the status (in production, update DB)
    print(f"Call {CallSid}: {CallStatus}")

    if ErrorCode:
        print(f"  Error: {ErrorCode} - {ErrorMessage}")

    if CallDuration:
        print(f"  Duration: {CallDuration}s")

    # Return empty TwiML
    return twiml_response('<?xml version="1.0" encoding="UTF-8"?><Response></Response>')


@router.post("/amd")
async def amd_webhook(
    CallSid: str = Form(...),
    AnsweredBy: str = Form(...),
) -> Response:
    """
    Handle Answering Machine Detection results.

    AnsweredBy values:
    - human: A person answered
    - machine_start: Answering machine detected (start of message)
    - machine_end_beep: After the beep
    - machine_end_silence: After silence
    - machine_end_other: Other machine end
    - fax: Fax machine detected
    - unknown: Could not determine
    """
    print(f"AMD result for {CallSid}: {AnsweredBy}")

    if AnsweredBy == "human":
        # Human answered - connect to operator via conference
        return twiml_response('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Dial>
        <Conference beep="false" startConferenceOnEnter="true" endConferenceOnExit="true">
            room-{CallSid}
        </Conference>
    </Dial>
</Response>'''.replace("{CallSid}", CallSid))

    elif AnsweredBy in ("machine_start", "machine_end_beep", "machine_end_silence", "machine_end_other"):
        # Machine - hang up
        return twiml_response('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Hangup/>
</Response>''')

    elif AnsweredBy == "fax":
        # Fax - hang up
        return twiml_response('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Hangup/>
</Response>''')

    else:
        # Unknown - could try to connect anyway or hang up
        return twiml_response('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Hangup/>
</Response>''')


@router.post("/voice")
async def voice_webhook(
    CallSid: str = Form(...),
    From: str = Form(None),
    To: str = Form(None),
) -> Response:
    """
    Handle incoming voice call.

    This is the initial webhook when a call is answered.
    Returns TwiML instructions for the call.
    """
    print(f"Voice webhook: {CallSid} from {From} to {To}")

    # For outbound predictive dialing, we use AMD first
    # This TwiML enables machine detection
    return twiml_response('''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Pause length="1"/>
</Response>''')
