import os
from dotenv import load_dotenv

load_dotenv()

AZURE_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_REGION = os.getenv("AZURE_SPEECH_REGION")

# IDs DE ÁUDIO
#  para ver os IDs --> ( python -m sounddevice )


MIC_ID = 1                 # Microfone
VB_INPUT_ID = 11           # VB Cable Input (vai para Meet)
VB_OUTPUT_ID = 2           # Áudio do Meet
SPEAKER_ID = 5             # Fone

SAMPLE_RATE = 16000
CHANNELS = 1
