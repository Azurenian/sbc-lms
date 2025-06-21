"""
Handles text-to-speech integration for converting text to .mp3 audio using Edge TTS.
"""

import edge_tts
import pathlib

async def text_to_mp3(text: str, out_path: str) -> str:
    """
    Converts narration text to an .mp3 file using Edge TTS (en-US-AvaNeural).
    Returns the path to the generated audio file.
    """
    communicate = edge_tts.Communicate(text, voice="en-US-AvaNeural")
    await communicate.save(out_path)
    return out_path

if __name__ == "__main__":
    import asyncio
    sample_text = "This is a test of the Edge TTS text-to-speech system."
    output_path = "media/test_sample.mp3"
    pathlib.Path("media").mkdir(exist_ok=True)
    asyncio.run(text_to_mp3(sample_text, output_path))
