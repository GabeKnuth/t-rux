import wave
import struct
import math

def create_wav(filename, duration=1.0, freq=440.0, channels=1):
    sample_rate = 192000
    num_samples = int(sample_rate * duration)
    audio = []
    
    for i in range(num_samples):
        value = int(16000.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
        audio.append(value)
        if channels == 2:
            audio.append(value) # Duplicate for stereo

    with wave.open(filename, "w") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(struct.pack('<' + ('h' * len(audio)), *audio))
    print(f"Created {filename}")

create_wav("test_teddy.wav", freq=440.0)
create_wav("test_grubby.wav", freq=880.0)
create_wav("test_audio.wav", freq=220.0, channels=2) # Stereo source
