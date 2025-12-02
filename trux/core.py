"""
T-Rux Core Logic
Contains the signal processing and PPM generation classes.
"""

import logging
import math
import struct
import sys
import wave
from dataclasses import dataclass
from random import randint, uniform
from typing import Dict, List, Tuple, Optional

# --- Configuration & Constants ---

@dataclass
class Config:
    """Configuration constants for T-Rux."""
    # Audio Settings
    TARGET_SAMPLE_RATE: int = 192000
    
    # PPM Protocol Settings
    PPM_FRAME_WIDTH_SEC: float = 0.0225
    
    # Servo Timing (Microseconds)
    SERVO_MIN_US: int = 700
    SERVO_CENTER_US: int = 1100
    SERVO_MAX_US: int = 1500
    
    # Analysis Settings
    SMOOTHING_GROUP_SIZE: int = 9
    GRUBBY_ACTIVE_THRESHOLD: float = 1.5 # Amplitude threshold to consider Grubby "talking" (0-100 scale)
    
    # Channel Mapping
    # Teddy
    CH_TEDDY_EYES: int = 2
    CH_TEDDY_UPPER_JAW: int = 3
    CH_TEDDY_LOWER_JAW: int = 4
    
    # Grubby
    CH_GRUBBY_ACTIVE: int = 5 # Logic High if Grubby is speaking
    CH_GRUBBY_EYES: int = 6
    CH_GRUBBY_UPPER_JAW: int = 7
    CH_GRUBBY_LOWER_JAW: int = 8


# --- Signal Processing ---

def analyze_audio(input_path: str) -> Tuple[List[float], int]:
    """
    Reads the input WAV file and calculates the amplitude envelope.
    
    Returns:
        Tuple[List[float], int]: (Normalized amplitude list 0-100, sample_rate)
    """
    try:
        with wave.open(input_path, 'rb') as wav_file:
            params = wav_file.getparams()
            rate = params.framerate
            n_frames = params.nframes
            sampwidth = params.sampwidth
            n_channels = params.nchannels
            
            if rate < Config.TARGET_SAMPLE_RATE:
                logging.warning(
                    f"Input sample rate {rate} is lower than recommended {Config.TARGET_SAMPLE_RATE}. "
                    "Quality may be reduced."
                )
            
            # Read all frames
            raw_data = wav_file.readframes(n_frames)
            
    except Exception as e:
        logging.error(f"Failed to read input file {input_path}: {e}")
        sys.exit(1)

    # Parse audio data
    # Assuming 16-bit audio (short)
    if sampwidth != 2:
        logging.error(f"Input file {input_path} must be 16-bit WAV.")
        sys.exit(1)
        
    num_samples = len(raw_data) // 2
    fmt = f"<{num_samples}h"
    samples = struct.unpack(fmt, raw_data)
    
    # If stereo, take left channel only (stride 2)
    if n_channels > 1:
        samples = samples[::n_channels]
        
    # Calculate samples per PPM frame
    samples_per_frame = int(rate * Config.PPM_FRAME_WIDTH_SEC)
    
    # Calculate Amplitude Envelope
    envelope = []
    
    # Process in chunks (frames)
    for i in range(0, len(samples), samples_per_frame):
        chunk = samples[i:i + samples_per_frame]
        if not chunk:
            break
            
        # Max amplitude in this chunk (absolute value)
        max_amp = 0
        for s in chunk:
            abs_s = abs(s)
            if abs_s > max_amp:
                max_amp = abs_s
        
        envelope.append(max_amp)
        
    # Smoothing (Group Max)
    smoothed_envelope = []
    group_size = Config.SMOOTHING_GROUP_SIZE
    
    for i in range(0, len(envelope), group_size):
        group = envelope[i:i + group_size]
        if not group:
            break
        group_max = max(group)
        # Repeat for the whole group duration
        smoothed_envelope.extend([group_max] * len(group))
        
    # Normalize
    if not smoothed_envelope:
        return [], rate
        
    min_amp = min(smoothed_envelope)
    max_amp = max(smoothed_envelope)
    
    normalized = []
    if max_amp == min_amp:
        normalized = [0.0] * len(smoothed_envelope)
    else:
        scale = 100.0 / (max_amp - min_amp)
        for amp in smoothed_envelope:
            norm = (amp - min_amp) * scale
            normalized.append(norm)
            
    return normalized, rate


def generate_eye_movements(num_frames: int) -> List[int]:
    """Generates random eye blink patterns."""
    eyes = [Config.SERVO_MIN_US] * num_frames # Default open (700)
    
    # Constants for blinking
    BLINK_DURATION_FRAMES = 45 # ~1 second
    MIN_OPEN_FRAMES = 45
    MAX_OPEN_FRAMES = 300
    
    i = 0
    next_blink_in = randint(MIN_OPEN_FRAMES, MAX_OPEN_FRAMES)
    
    while i < num_frames:
        if next_blink_in <= 0:
            # Blink!
            end_blink = min(i + BLINK_DURATION_FRAMES, num_frames)
            for j in range(i, end_blink):
                eyes[j] = 1400 # Closed
            i = end_blink
            next_blink_in = randint(MIN_OPEN_FRAMES, MAX_OPEN_FRAMES)
        else:
            next_blink_in -= 1
            i += 1
            
    return eyes


def apply_upper_lip_wobble(amplitude_frames: List[float]) -> List[int]:
    """Adds random variation to the upper lip to make it look more organic."""
    wobbled = []
    
    for amp in amplitude_frames:
        divisor = uniform(1.0, 2.14)
        
        # Map 0-100 back to 700-1500 range
        raw_servo = 700 + (amp / 100.0 * 800)
        
        val = int(raw_servo / divisor)
        
        # Clip to min
        if val < 700:
            val = 700
            
        wobbled.append(val)
    
    return wobbled


def process_character(input_path: str, is_grubby: bool = False) -> Tuple[List[int], List[int], List[int], List[float]]:
    """
    Analyzes audio for a character and returns servo positions.
    Returns: (eyes_us, upper_jaw_us, lower_jaw_us, amplitude_envelope)
    """
    amplitude_envelope, _ = analyze_audio(input_path)
    num_frames = len(amplitude_envelope)
    
    # Eyes
    eye_pos_us = generate_eye_movements(num_frames)
    
    # Upper Jaw (Wobble)
    upper_jaw_us = apply_upper_lip_wobble(amplitude_envelope)
    
    # Lower Jaw (Direct mapping)
    lower_jaw_us = []
    for amp in amplitude_envelope:
        val = 700 + (amp / 100.0 * 800)
        lower_jaw_us.append(val)
        
    return eye_pos_us, upper_jaw_us, lower_jaw_us, amplitude_envelope


# --- PPM Generation ---

class PPMGenerator:
    def __init__(self, sample_rate: int = 192000, invert: bool = False):
        self.sample_rate = sample_rate
        self.invert = invert
        self.samples_per_frame = int(Config.PPM_FRAME_WIDTH_SEC * sample_rate)
        
        # Calculate sample counts for pulse components
        # mmdiv = rate / 10000 -> 19.2 samples per "unit"
        self.mmdiv = sample_rate / 10000.0
        self.amplitude = 20262  # Max amplitude for signal
        
    def _generate_frame_bytes_16bit(self, channels: Dict[int, float]) -> bytes:
        pulse_sequence = []
        high = self.amplitude if not self.invert else -self.amplitude
        low = -self.amplitude if not self.invert else self.amplitude
        
        # Start Pulse
        pulse_sequence.extend([high] * int(self.mmdiv * 4))
        
        # Channels 1-8
        for i in range(1, 9):
            val = channels.get(i, 0.0)
            
            # Separator
            pulse_sequence.extend([low] * int(self.mmdiv * 7))
            
            # Pulse Width
            signal_len = int(self.mmdiv * 10 * (val * 0.75 / 100.0))
            
            pulse_sequence.extend([low] * signal_len)
            pulse_sequence.extend([high] * int(self.mmdiv * 4))
            
        # Padding
        current_len = len(pulse_sequence)
        padding = self.samples_per_frame - current_len
        if padding > 0:
            pulse_sequence.extend([0] * padding)
            
        # Pack as 16-bit integers (short)
        return struct.pack('<' + 'h' * len(pulse_sequence), *pulse_sequence)

    def generate_wav(self, output_path: str, frame_data: List[Dict[int, float]], audio_source_path: Optional[str] = None):
        """
        Writes the generated PPM frames to a WAV file.
        If audio_source_path is provided, generates a Stereo file (Left=PPM, Right=Audio).
        Otherwise, generates a Mono file (PPM only).
        """
        logging.info(f"Generating PPM signal for {len(frame_data)} frames...")
        
        # Prepare Audio Source if needed
        audio_samples = []
        if audio_source_path:
            try:
                with wave.open(audio_source_path, 'rb') as af:
                    if af.getframerate() != self.sample_rate:
                        logging.warning(f"Audio source sample rate {af.getframerate()} does not match target {self.sample_rate}. Sync issues may occur.")
                    
                    # Read all audio frames
                    raw_audio = af.readframes(af.getnframes())
                    
                    # Unpack
                    # Assuming 16-bit
                    if af.getsampwidth() != 2:
                        logging.error("Audio source must be 16-bit WAV.")
                        sys.exit(1)
                        
                    n_audio_samples = len(raw_audio) // 2
                    unpacked_audio = struct.unpack(f"<{n_audio_samples}h", raw_audio)
                    
                    # If stereo, mix to mono or take left? Let's take left for simplicity or mix.
                    # Taking left channel if stereo
                    if af.getnchannels() > 1:
                        audio_samples = list(unpacked_audio[::af.getnchannels()])
                    else:
                        audio_samples = list(unpacked_audio)
                        
            except Exception as e:
                logging.error(f"Failed to read audio source: {e}")
                sys.exit(1)

        try:
            with wave.open(output_path, 'wb') as wav_file:
                if audio_source_path:
                    wav_file.setnchannels(2) # Stereo
                else:
                    wav_file.setnchannels(1) # Mono
                    
                wav_file.setsampwidth(2) # 16-bit
                wav_file.setframerate(self.sample_rate)
                
                # Generate PPM bytes frame by frame
                total_ppm_samples = 0
                
                for i, channels in enumerate(frame_data):
                    ppm_bytes = self._generate_frame_bytes_16bit(channels)
                    
                    if not audio_source_path:
                        wav_file.writeframes(ppm_bytes)
                    else:
                        # Interleave PPM (Left) and Audio (Right)
                        # ppm_bytes is a byte string of 16-bit integers
                        # We need to unpack it to interleave
                        n_ppm = len(ppm_bytes) // 2
                        ppm_ints = struct.unpack(f"<{n_ppm}h", ppm_bytes)
                        
                        stereo_frame = []
                        for j, ppm_val in enumerate(ppm_ints):
                            # Get corresponding audio sample
                            # We need to track global sample index
                            global_idx = total_ppm_samples + j
                            
                            audio_val = 0
                            if global_idx < len(audio_samples):
                                audio_val = audio_samples[global_idx]
                            
                            # Left = PPM, Right = Audio
                            stereo_frame.append(ppm_val)
                            stereo_frame.append(audio_val)
                        
                        total_ppm_samples += n_ppm
                        
                        # Pack stereo frame
                        stereo_bytes = struct.pack(f"<{len(stereo_frame)}h", *stereo_frame)
                        wav_file.writeframes(stereo_bytes)
                        
        except Exception as e:
            logging.error(f"Failed to write output file: {e}")
            sys.exit(1)
