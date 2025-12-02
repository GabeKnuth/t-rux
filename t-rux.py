#!/usr/bin/env python3
"""
T-Rux: Teddy Ruxpin Audio to PPM Converter

This script analyzes voice recordings (WAV) and generates a Pulse Position Modulation (PPM)
audio signal used to control a Teddy Ruxpin bear and his friend Grubby.

Usage:
    python t-rux.py --output output.wav [--teddy teddy.wav] [--grubby grubby.wav] [--audio audio.wav]
"""

import argparse
import logging
import sys
from typing import List, Dict, Tuple

from trux.core import Config, analyze_audio, process_character, PPMGenerator

# --- Main Execution ---

def main():
    # Check if any arguments were provided
    if len(sys.argv) == 1:
        # No arguments -> Launch GUI
        try:
            from trux.gui import main as gui_main
            gui_main()
            return
        except ImportError as e:
            logging.error(f"Failed to launch GUI: {e}")
            logging.error("Ensure dependencies are installed: pip install -r requirements.txt")
            sys.exit(1)
        except Exception as e:
            logging.error(f"GUI Error: {e}")
            sys.exit(1)

    parser = argparse.ArgumentParser(description="Generate Teddy Ruxpin PPM control signals from audio.")
    parser.add_argument("--output", required=False, help="Output WAV file path")
    parser.add_argument("--teddy", help="Input WAV file for Teddy's voice (optional)")
    parser.add_argument("--grubby", help="Input WAV file for Grubby's voice (optional)")
    parser.add_argument("--audio", help="Final audio track to merge into Right channel (optional)")
    parser.add_argument("--invert", action="store_true", help="Invert the PPM signal (for some setups)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    # Legacy positional arguments support
    parser.add_argument("legacy_input", nargs='?', help="Legacy: Input WAV file")
    parser.add_argument("legacy_output", nargs='?', help="Legacy: Output WAV file")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Handle Legacy vs New Mode
    final_output = args.output or args.legacy_output
    final_teddy = args.teddy or args.legacy_input
    final_grubby = args.grubby
    
    if not final_output:
        parser.error("Output file is required (either as second positional arg or --output)")
        
    if not final_teddy and not final_grubby:
        parser.error("At least one input (Teddy or Grubby) is required.")

    # Processing
    frames_data = []
    
    teddy_data = None
    grubby_data = None
    sample_rate = Config.TARGET_SAMPLE_RATE
    
    if final_teddy:
        print(f"Processing Teddy: {final_teddy}...")
        t_eyes, t_upper, t_lower, t_amp = process_character(final_teddy)
        teddy_data = (t_eyes, t_upper, t_lower, t_amp)
        _, sample_rate = analyze_audio(final_teddy)
        
    if final_grubby:
        print(f"Processing Grubby: {final_grubby}...")
        g_eyes, g_upper, g_lower, g_amp = process_character(final_grubby, is_grubby=True)
        grubby_data = (g_eyes, g_upper, g_lower, g_amp)
        if not final_teddy:
             _, sample_rate = analyze_audio(final_grubby)

    # Determine max frames
    num_frames = 0
    if teddy_data:
        num_frames = max(num_frames, len(teddy_data[0]))
    if grubby_data:
        num_frames = max(num_frames, len(grubby_data[0]))
        
    # Build Frames
    for i in range(num_frames):
        frame = {}
        
        # Teddy Channels
        if teddy_data and i < len(teddy_data[0]):
            frame[Config.CH_TEDDY_EYES] = (teddy_data[0][i] - 700) / 8.0
            frame[Config.CH_TEDDY_UPPER_JAW] = (teddy_data[1][i] - 700) / 8.0
            frame[Config.CH_TEDDY_LOWER_JAW] = (teddy_data[2][i] - 700) / 8.0
        else:
            # Default positions
            frame[Config.CH_TEDDY_EYES] = (Config.SERVO_MIN_US - 700) / 8.0
            frame[Config.CH_TEDDY_UPPER_JAW] = (Config.SERVO_MIN_US - 700) / 8.0
            frame[Config.CH_TEDDY_LOWER_JAW] = (Config.SERVO_MIN_US - 700) / 8.0

        # Grubby Channels
        if grubby_data and i < len(grubby_data[0]):
            frame[Config.CH_GRUBBY_EYES] = (grubby_data[0][i] - 700) / 8.0
            frame[Config.CH_GRUBBY_UPPER_JAW] = (grubby_data[1][i] - 700) / 8.0
            frame[Config.CH_GRUBBY_LOWER_JAW] = (grubby_data[2][i] - 700) / 8.0
            
            # Channel 5 Logic: Active if amplitude > Threshold
            if grubby_data[3][i] > Config.GRUBBY_ACTIVE_THRESHOLD:
                frame[Config.CH_GRUBBY_ACTIVE] = (Config.SERVO_MAX_US - 700) / 8.0
            else:
                frame[Config.CH_GRUBBY_ACTIVE] = (Config.SERVO_MIN_US - 700) / 8.0
        else:
            frame[Config.CH_GRUBBY_EYES] = (Config.SERVO_MIN_US - 700) / 8.0
            frame[Config.CH_GRUBBY_UPPER_JAW] = (Config.SERVO_MIN_US - 700) / 8.0
            frame[Config.CH_GRUBBY_LOWER_JAW] = (Config.SERVO_MIN_US - 700) / 8.0
            frame[Config.CH_GRUBBY_ACTIVE] = (Config.SERVO_MIN_US - 700) / 8.0
            
        frames_data.append(frame)
        
    # Generate Output
    print(f"Generating output to {final_output}...")
    if args.audio:
        print(f"Merging with audio source: {args.audio}")
        
    ppm_gen = PPMGenerator(sample_rate=sample_rate, invert=args.invert)
    ppm_gen.generate_wav(final_output, frames_data, audio_source_path=args.audio)
    
    print("Done!")

if __name__ == "__main__":
    main()

