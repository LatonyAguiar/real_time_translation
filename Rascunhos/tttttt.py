# import azure.cognitiveservices.speech as speechsdk
# import logging
# import time
# import sounddevice as sd
# import numpy as np
# import os
# from config import AZURE_KEY, AZURE_REGION

# # =============================
# # LOG
# # =============================
# logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# # =============================
# # 1. TRADUTOR: VOCÊ -> GRINGO (PT-BR para EN)
# # =============================
# translation_config = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
# translation_config.speech_recognition_language = "pt-BR"
# translation_config.add_target_language("en")

# # Usa seu microfone padrão (ME6S) configurado no Windows
# audio_input = speechsdk.audio.AudioConfig(use_default_microphone=True)
# recognizer = speechsdk.translation.TranslationRecognizer(translation_config=translation_config, audio_config=audio_input)

# def synthesize_to_vbcable(text: str):
#     speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
#     speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
#     synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
#     result = synthesizer.speak_text_async(text).get()
#     if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
#         audio_array = np.frombuffer(result.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
#         # 🔊 ID 9: CABLE Input (Envia para o Gringo no Meet)
#         sd.play(audio_array, samplerate=16000, device=9) 

# def recognized(evt):
#     if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
#         translated = evt.result.translations.get("en")
#         if translated:
#             logging.info(f"VOCÊ DISSE (PT): {evt.result.text}")
#             logging.info(f"TRADUZIDO (EN): {translated}")
#             synthesize_to_vbcable(translated)

# # =============================
# # 2. TRADUTOR: GRINGO -> VOCÊ (EN para PT-BR)
# # =============================
# translation_config_gringo = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
# translation_config_gringo.speech_recognition_language = "en-US"
# translation_config_gringo.add_target_language("pt-BR")

# push_stream = speechsdk.audio.PushAudioInputStream()
# gringo_audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

# def synthesize_to_headphones(text: str):
#     speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
#     speech_config.speech_synthesis_voice_name = "pt-BR-FranciscaNeural"
#     synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
#     result = synthesizer.speak_text_async(text).get()
#     if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
#         audio_array = np.frombuffer(result.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
#         # 🔊 ID 5: Seus Fones de Ouvido (Você ouve a tradução)
#         sd.play(audio_array, samplerate=16000, device=5) 

# def gringo_recognized(evt):
#     if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
#         translated = evt.result.translations.get("pt-BR")
#         if translated:
#             logging.info(f"GRINGO DISSE (EN): {evt.result.text}")
#             logging.info(f"TRADUZIDO (PT): {translated}")
#             synthesize_to_headphones(translated)

# format_azure = speechsdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
# push_stream = speechsdk.audio.PushAudioInputStream(stream_format=format_azure)

# def audio_bridge_callback(indata, frames, time, status):
#     if status:
#         logging.warning(status)
    
#     # 1. Normalização e Limpeza
#     audio_fp32 = indata.flatten().astype(np.float32)
    
#     # 2. RESAMPLING (Crucial: de 44100Hz para 16000Hz)
#     # Sem isso, o Azure não reconhece a fala do gringo
#     num_samples = int(len(audio_fp32) * 16000 / 44100)
#     audio_resampled = signal.resample(audio_fp32, num_samples)
    
#     # 3. Conversão para PCM 16 bits (O que o Azure entende)
#     audio_int16 = (audio_resampled * 32767).astype(np.int16)
    
#     # 4. Threshold de silêncio para evitar gastar API com ruído
#     if np.max(np.abs(audio_int16)) > 500: # Ajuste se necessário
#         push_stream.write(audio_int16.tobytes())

# # --- CONFIGURAÇÃO DOS RECOGNIZERS ---
# # Gringo (EN-US) -> Você (PT-BR)
# translation_config_gringo = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
# translation_config_gringo.speech_recognition_language = "en-US"
# translation_config_gringo.add_target_language("pt-BR")
# translation_config_gringo.voice_name = "pt-BR-FranciscaNeural"

# gringo_audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
# gringo_recognizer = speechsdk.translation.TranslationRecognizer(
#     translation_config=translation_config_gringo, 
#     audio_config=gringo_audio_config
# )

# # =============================
# # EXECUÇÃO E CONFIGURAÇÃO DE HARDWARE
# # =============================
# recognizer.recognized.connect(recognized)
# gringo_recognizer.recognized.connect(gringo_recognized)

# # 🚀 ID 32: CABLE Output (Abre na taxa nativa do Windows para evitar erro -9997)
# try:
#     # Tenta 44100Hz (Padrão Windows)
#     gringo_input_stream = sd.InputStream(
#         device=32, channels=1, samplerate=44100, dtype='int16', callback=audio_bridge_callback
#     )
# except:
#     # Tenta 48000Hz (Alternativa Windows)
#     gringo_input_stream = sd.InputStream(
#         device=32, channels=1, samplerate=48000, dtype='int16', callback=audio_bridge_callback
#     )

# logging.info("🎤 SISTEMA ATIVADO!")
# logging.info("-> Use Saída CABLE Input no Meet")
# logging.info("-> Use Entrada CABLE Output no Meet")

# recognizer.start_continuous_recognition()
# gringo_recognizer.start_continuous_recognition()
# gringo_input_stream.start()

# try:
#     while True:
#         time.sleep(0.5)
# except KeyboardInterrupt:
#     gringo_input_stream.stop()
#     recognizer.stop_continuous_recognition()
#     gringo_recognizer.stop_continuous_recognition()
#     logging.info("Encerrado.")

























import azure.cognitiveservices.speech as speechsdk
import logging
import time
import sounddevice as sd
import numpy as np
import scipy.signal as signal
from config import AZURE_KEY, AZURE_REGION

# =============================
# CONFIGURAÇÃO DE LOGS
# =============================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

estou_falando = False
taxa_entrada_real = 44100 

# IDs de Hardware baseados na sua lista
ID_CABLE_OUT_GRINGO = 2   # MME
ID_FONES_USUARIO = 5      # Seus fones
ID_CABLE_IN_MEET = 9      # Entrada do Meet

# =============================
# 1. TRADUTOR: VOCÊ -> GRINGO
# =============================
trans_vc_config = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
trans_vc_config.speech_recognition_language = "pt-BR"
trans_vc_config.add_target_language("en")

audio_input_vc = speechsdk.audio.AudioConfig(use_default_microphone=True)
recognizer_vc = speechsdk.translation.TranslationRecognizer(translation_config=trans_vc_config, audio_config=audio_input_vc)

def synthesize_to_vbcable(text_en: str):
    """Sintetiza a tradução para o Gringo ouvir no Meet (ID 9)"""
    global estou_falando
    if not text_en: return
    
    estou_falando = True
    cfg = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    cfg.speech_synthesis_voice_name = "en-US-JennyNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
    
    result = synthesizer.speak_text_async(text_en).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_data = np.frombuffer(result.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio_data, samplerate=16000, device=ID_CABLE_IN_MEET)
        sd.wait() 
    
    estou_falando = False

def on_recognized_vc(evt):
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        traducao = evt.result.translations.get("en")
        if traducao:
            logging.info(f"VOCÊ DISSE (PT): {evt.result.text}")
            logging.info(f"TRADUÇÃO -> GRINGO: {traducao}")
            synthesize_to_vbcable(traducao)

# =============================
# 2. TRADUTOR: GRINGO -> VOCÊ
# =============================
trans_gr_config = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
trans_gr_config.speech_recognition_language = "en-US"
trans_gr_config.add_target_language("pt-BR")

format_azure = speechsdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
push_stream = speechsdk.audio.PushAudioInputStream(stream_format=format_azure)
audio_input_gr = speechsdk.audio.AudioConfig(stream=push_stream)

def synthesize_to_headphones(text_pt: str):
    """Sintetiza a tradução para VOCÊ ouvir no fone (ID 5)"""
    if not text_pt: return
    
    cfg = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    cfg.speech_synthesis_voice_name = "pt-BR-FranciscaNeural"
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
    
    result = synthesizer.speak_text_async(text_pt).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        audio_data = np.frombuffer(result.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio_data, samplerate=16000, device=ID_FONES_USUARIO)

def on_recognized_gr(evt):
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        traducao = evt.result.translations.get("pt-BR")
        if traducao:
            logging.info(f"GRINGO DISSE (EN): {evt.result.text}")
            logging.info(f"TRADUÇÃO -> VOCÊ: {traducao}")
            synthesize_to_headphones(traducao)

recognizer_gr = speechsdk.translation.TranslationRecognizer(translation_config=trans_gr_config, audio_config=audio_input_gr)

# =============================
# PONTE DE ÁUDIO
# =============================
def audio_bridge_callback(indata, frames, time, status):
    if status:
        logging.warning(f"Status do áudio: {status}")
    
    if estou_falando:
        return

    # 1. Converte para Float32 para um resampling de qualidade
    audio_fp32 = indata.flatten().astype(np.float32)
    
    # 2. Resampling de alta fidelidade
    num_samples = int(len(audio_fp32) * 16000 / taxa_entrada_real)
    audio_resampled = signal.resample(audio_fp32, num_samples)
    
    # 3. Volta para Int16 (formato que o Azure exige)
    audio_int16 = audio_resampled.astype(np.int16)
    
    # 4. Envia para o Azure
    push_stream.write(audio_int16.tobytes())


# Adicione este log para debug em tempo real
def gringo_recognizing_handler(evt):
    # Isso mostra que o Azure está OUVINDO, mesmo antes de terminar a frase
    if evt.result.text:
        print(f"--- Azure ouvindo gringo: {evt.result.text[:50]}...", end='\r')

recognizer_gr.recognizing.connect(gringo_recognizing_handler)

# =============================
# INICIALIZAÇÃO
# =============================
recognizer_vc.recognized.connect(on_recognized_vc)
recognizer_gr.recognized.connect(on_recognized_gr)



gringo_input_stream = sd.InputStream(
    device=ID_CABLE_OUT_GRINGO, 
    channels=1, 
    samplerate=taxa_entrada_real, 
    dtype='int16', 
    callback=audio_bridge_callback
)

logging.info(f"✅ Conectado ao Cabo Virtual (ID {ID_CABLE_OUT_GRINGO})")
logging.info("🚀 SISTEMA OPERACIONAL")

recognizer_vc.start_continuous_recognition()
recognizer_gr.start_continuous_recognition()


gringo_input_stream.start()

try:
    while True: time.sleep(0.5)
except KeyboardInterrupt:
    gringo_input_stream.stop()
    logging.info("Encerrado.")



















    