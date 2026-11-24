from pydantic import BaseModel


class WipeOut(BaseModel):
    devices_notified: int
