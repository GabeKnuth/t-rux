"""
T-Rux Audio Engine
Handles loading, editing, and exporting audio using NumPy.
"""

import logging
import numpy as np
import soundfile as sf
import sounddevice as sd
from typing import Optional, Tuple

class AudioEngine:
    def __init__(self):
        self.data: Optional[np.ndarray] = None
        self.sample_rate: int = 44100
        self.original_path: Optional[str] = None
        
    def load_file(self, path: str) -> bool:
        """Loads a WAV file into a float32 numpy array."""
        try:
            data, samplerate = sf.read(path, dtype='float32')
            
            # Ensure mono for simplicity in visualization/editing for now
            # If stereo, we can keep it, but for T-Rux analysis we usually want mono.
            # Let's keep it as is, but handle dimensions.
            if data.ndim > 1:
                # If multi-channel, we can just keep it. 
                # But for visualization, we might want to just show one channel or mix.
                pass
                
            self.data = data
            self.sample_rate = samplerate
            self.original_path = path
            logging.info(f"Loaded {path}: {self.data.shape} @ {self.sample_rate}Hz")
            return True
        except Exception as e:
            logging.error(f"Failed to load audio {path}: {e}")
            return False

    def get_duration(self) -> float:
        if self.data is None:
            return 0.0
        return len(self.data) / self.sample_rate

    def mute_region(self, start_sec: float, end_sec: float):
        """Mutes the audio in the given time range."""
        if self.data is None:
            return
            
        start_idx = int(start_sec * self.sample_rate)
        end_idx = int(end_sec * self.sample_rate)
        
        # Clamp
        start_idx = max(0, start_idx)
        end_idx = min(len(self.data), end_idx)
        
        if start_idx >= end_idx:
            return
            
        self.data[start_idx:end_idx] = 0.0
        logging.info(f"Muted region {start_sec:.2f}s - {end_sec:.2f}s")

    def amplify_region(self, start_sec: float, end_sec: float, factor: float):
        """Amplifies the audio in the given time range."""
        if self.data is None:
            return
            
        start_idx = int(start_sec * self.sample_rate)
        end_idx = int(end_sec * self.sample_rate)
        
        # Clamp
        start_idx = max(0, start_idx)
        end_idx = min(len(self.data), end_idx)
        
        if start_idx >= end_idx:
            return
            
        self.data[start_idx:end_idx] *= factor
        
        # Clip to -1.0 to 1.0 to avoid distortion
        np.clip(self.data[start_idx:end_idx], -1.0, 1.0, out=self.data[start_idx:end_idx])
        
        logging.info(f"Amplified region {start_sec:.2f}s - {end_sec:.2f}s by {factor}x")

    def export(self, path: str):
        """Exports the current audio data to a WAV file."""
        if self.data is None:
            return
            
        try:
            # sf.write expects data, samplerate
            sf.write(path, self.data, self.sample_rate)
            logging.info(f"Exported to {path}")
        except Exception as e:
            logging.error(f"Failed to export audio: {e}")

    def play(self, start_sec: float = 0.0, end_sec: Optional[float] = None):
        """Plays the audio from start_sec."""
        if self.data is None:
            return
            
        start_idx = int(start_sec * self.sample_rate)
        end_idx = int(end_sec * self.sample_rate) if end_sec else len(self.data)
        
        # Stop any current playback
        sd.stop()
        
        # Play asynchronously
        sd.play(self.data[start_idx:end_idx], self.sample_rate)

    def stop(self):
        sd.stop()
