import azure.cognitiveservices.speech as speechsdk
import logging
import time
import sounddevice as sd
import numpy as np
import os
from config import AZURE_KEY, AZURE_REGION

# =============================
# LOG
# =============================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# =============================
# 1. TRADUTOR: VOCÊ -> GRINGO (PT-BR para EN)
# =============================
translation_config = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
translation_config.speech_recognition_language = "pt-BR"
translation_config.add_target_language("en")

audio_input = speechsdk.audio.AudioConfig(use_default_microphone=True)
recognizer = speechsdk.translation.TranslationRecognizer(translation_config=translation_config, audio_config=audio_input)

def synthesize_to_vbcable(text: str):
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_array = np.frombuffer(result.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio_array, samplerate=16000, device=8) # ID 8: CABLE Input

def recognized(evt):
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        translated = evt.result.translations.get("en")
        if translated:
            logging.info(f"VOCÊ DISSE (PT): {evt.result.text}")
            logging.info(f"TRADUZIDO (EN): {translated}")
            synthesize_to_vbcable(translated)

# =============================
# 2. TRADUTOR: GRINGO -> VOCÊ (EN para PT-BR)
# =============================
# Criando a config que estava faltando:
translation_config_gringo = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
translation_config_gringo.speech_recognition_language = "en-US"
translation_config_gringo.add_target_language("pt-BR")

# Usando seu ID Real do PowerShell
gringo_device_id = "{0.0.1.00000000}.{4A1EF699-487B-419F-BB2B-C1536C2A5818}"
gringo_audio_config = speechsdk.audio.AudioConfig(device_name=gringo_device_id)

def synthesize_to_headphones(text: str):
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    speech_config.speech_synthesis_voice_name = "pt-BR-FranciscaNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_array = np.frombuffer(result.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio_array, samplerate=16000, device=9) # ID 9: Seu Fone

def gringo_recognized(evt):
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        translated = evt.result.translations.get("pt-BR")
        if translated:
            logging.info(f"GRINGO DISSE (EN): {evt.result.text}")
            logging.info(f"TRADUZIDO (PT): {translated}")
            synthesize_to_headphones(translated)

# Inicializando o reconhecedor do gringo
gringo_recognizer = speechsdk.translation.TranslationRecognizer(translation_config=translation_config_gringo, audio_config=gringo_audio_config)

# =============================
# EXECUÇÃO
# =============================
recognizer.recognized.connect(recognized)
gringo_recognizer.recognized.connect(gringo_recognized)

logging.info("🎤 SISTEMA ATIVADO!")
logging.info("- Falando em PT-BR (Seu Mic) -> Saindo no CABLE Input (ID 8)")
logging.info("- Ouvindo em EN (CABLE Output) -> Saindo no seu Fone (ID 9)")

recognizer.start_continuous_recognition()
gringo_recognizer.start_continuous_recognition()

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    recognizer.stop_continuous_recognition()
    gringo_recognizer.stop_continuous_recognition()
    logging.info("Encerrado.")