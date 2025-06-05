import asyncio
import os
from typing import Union

from pytgcalls import PyTgCalls, idle
from pytgcalls.types import MediaStream, GroupCallConfig

from telethon import TelegramClient
from telethon.tl.types import (
    InputPeerChannel, InputPeerChat, InputGroupCall,
    PeerChannel, PeerChat
)
from telethon.tl.functions.phone import GetGroupCallRequest, DiscardGroupCallRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest


# Load environment variables
api_id: int = int(os.getenv("TG_API_ID"))
api_hash: str = os.getenv("TG_API_HASH")
chat_id: int = int(os.getenv("TG_CHAT_ID"))
audio_url: str = os.getenv("TG_AUDIO_URL")
session_name: str = os.getenv("TG_SESSION_NAME", "default_session")
duration: int = int(os.getenv("TG_SESSION_DURATION", "10"))  # Default to 10 seconds if not set

client = TelegramClient(session_name, api_id, api_hash)

async def get_input_peer(entity) -> Union[InputPeerChannel, InputPeerChat]:
    """Returns the correct InputPeer type based on chat type."""
    if hasattr(entity, 'megagroup') or hasattr(entity, 'broadcast'):
        return InputPeerChannel(channel_id=entity.id, access_hash=entity.access_hash)
    return InputPeerChat(chat_id=entity.id)

async def discard_group_call(input_peer: Union[InputPeerChannel, InputPeerChat], entity):
    """Attempts to discard the group call."""
    try:
        if isinstance(input_peer, InputPeerChannel):
            full = await client(GetFullChannelRequest(channel=input_peer))
        else:
            full = await client(GetFullChatRequest(chat_id=entity.id))

        call_info = full.full_chat.call
        input_group_call = InputGroupCall(id=call_info.id, access_hash=call_info.access_hash)
        await client(DiscardGroupCallRequest(call=input_group_call))
        print("Group call fully discarded.")
    except Exception as e:
        print(f"Failed to discard group call: {e}")

async def try_play_with_retries(app, chat_id, stream, config, retries=10, delay=5):
    """Attempts to start the audio stream with retries."""
    for attempt in range(1, retries + 1):
        try:
            print(f"Attempt {attempt} to start audio stream...")
            await asyncio.wait_for(app.play(chat_id, stream, config), timeout=15)
            print("Audio stream started successfully.")
            return True
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt < retries:
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
    print("All attempts to start audio stream failed.")
    return False

async def main():
    try:
        # 1. Start Telethon client
        await client.start()
        print("Telethon client started.")

        # 2. Get chat entity and input peer
        entity = await client.get_entity(chat_id)
        input_peer = await get_input_peer(entity)

        # 3. Initialize and start PyTgCalls
        app = PyTgCalls(client)
        await app.start()
        print("PyTgCalls started.")

        # 4. Start streaming audio to group call with retries
        stream = MediaStream(audio_url, video_flags=MediaStream.Flags.IGNORE)
        config = GroupCallConfig(join_as=input_peer, auto_start=True)

        success = await try_play_with_retries(app, chat_id, stream, config)

        if not success:
            await client.disconnect()
            return

        # 5. Wait for duration (e.g. stream length or test period)
        await asyncio.sleep(duration)

    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Cleaning up...")
    finally:
       # 6. Attempt to discard group call
       await discard_group_call(input_peer, entity)

       # 7. Disconnect Telethon
       await client.disconnect()
       print("Telethon client disconnected.")

if __name__ == '__main__':
    asyncio.run(main())
