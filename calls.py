import asyncio
import os
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import MediaStream, GroupCallConfig

from telethon import TelegramClient
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputGroupCall
from telethon.tl.functions.phone import GetGroupCallRequest, DiscardGroupCallRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")
chat_id = int(os.getenv("TG_CHAT_ID"))
audio_url = os.getenv("TG_AUDIO_URL")
session_name = os.getenv("TG_SESSION_NAME", "default_session")

client = TelegramClient(session_name, api_id, api_hash)

async def main():
    # 1) Start Telethon client
    await client.start()

    # 2) Get entity and input_peer for PyTgCalls
    entity = await client.get_entity(chat_id)
    if hasattr(entity, 'megagroup') or hasattr(entity, 'broadcast'):
        # If it's a Supergroup or Channel
        input_peer = InputPeerChannel(channel_id=entity.id, access_hash=entity.access_hash)
    else:
        # If it's a basic group
        input_peer = InputPeerChat(chat_id=entity.id)

    # 3) Start PyTgCalls
    app = PyTgCalls(client)
    await app.start()
    print("PyTgCalls has started.")

    # 4) Join the group call and start streaming audio
    await app.play(
        chat_id,
        MediaStream(
            audio_url,
            video_flags=MediaStream.Flags.IGNORE
        ),
        config=GroupCallConfig(join_as=input_peer, auto_start=True)
    )
    print("Audio stream playback started.")

    # 5) Wait for 10 seconds to let WebRTC establish the stream
    await asyncio.sleep(10)

    # 6) Discard group call for everyone
    try:
        if isinstance(input_peer, InputPeerChannel):
            full = await client(GetFullChannelRequest(channel=input_peer))
            call_info = full.full_chat.call
        else:
            full = await client(GetFullChatRequest(chat_id=entity.id))
            call_info = full.full_chat.call

        input_group_call = InputGroupCall(
            id=call_info.id,
            access_hash=call_info.access_hash
        )
        await client(DiscardGroupCallRequest(call=input_group_call))
        print("Group call fully discarded (DiscardGroupCall).")
    except Exception as e:
        print(f"Failed to discard group call (possibly no rights or already ended): {e}")

    # 7) Disconnect Telethon client
    await client.disconnect()
    print("Telethon client disconnected.")

if __name__ == '__main__':
    asyncio.run(main())
