import logging
from datetime import datetime, timedelta

from beanie import PydanticObjectId
from fastapi import APIRouter
from starlette.responses import Response

from sletmaster.bot.client import bot_client
from sletmaster.models import Event, EventStatus

bot_router = APIRouter()
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)


@bot_router.put("/link/{event_id}/{tg_id}")
async def create_link(event_id: str, tg_id: str):
    event = await Event.get(PydanticObjectId(event_id))
    if event is None:
        return Response(status_code=404, content=f"Event {event_id} not found")
    event.tg_owner = tg_id
    await event.save()
    return {
        "event_name": event.name
    }


@bot_router.put("/status/{event_id}/{status}")
async def status_response(event_id: str, status: EventStatus):
    event = await Event.get(PydanticObjectId(event_id))
    if event is None:
        return Response(status_code=404, content=f"Event {event_id} not found")
    event.status = status
    event.status_time = datetime.now()
    await event.save()
    return {
        "name": event.name
    }


@bot_router.get("/check_event/{event_id}")
async def check_event(event_id: str):
    event = await Event.get(PydanticObjectId(event_id))
    if event is None:
        return Response(status_code=404, content=f"Event {event_id} not found")
    event.last_tg_ping = datetime.now()
    await Event.update(event)
    await bot_client.check_event_status(event)


@bot_router.get("/check_events/99e7a75a477cfb0e67ec7d7862a5a4268a3edbf04e98937e5aa1ada3f7df881a")
async def check_events():
    threshold = timedelta(minutes=5)
    async for event in Event.find():
        logger.info("Checking event '%s' with status '%s'", event.id, event.status)
        if not event.status == "created":
            continue
        time_left: timedelta = event.start_time - datetime.now()
        logger.info("time_left = %s", time_left)
        logger.info("time_left.seconds = %d threshold.seconds = %d", time_left.total_seconds(),
                    threshold.total_seconds())
        if 0 <= time_left.total_seconds() <= threshold.total_seconds() and event.tg_owner is not None and event.tg_owner != '0':
            event.last_tg_ping = datetime.now()
            try:
                await bot_client.check_event_status(event)
                await event.save()
            except Exception:
                logger.exception("Failed to send check event message")
