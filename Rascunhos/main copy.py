import azure.cognitiveservices.speech as speechsdk
import logging
import time
import os
from config import AZURE_KEY, AZURE_REGION

# =============================
# LOG
# =============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =============================
# CONFIGURAÇÃO DE TRADUÇÃO
# =============================
translation_config = speechsdk.translation.SpeechTranslationConfig(
    subscription=AZURE_KEY,
    region=AZURE_REGION
)

translation_config.speech_recognition_language = "pt-BR"
translation_config.add_target_language("en")

# =============================
# MICROFONE FÍSICO (DEFAULT)
# =============================
audio_input = speechsdk.audio.AudioConfig(
    use_default_microphone=True
)

recognizer = speechsdk.translation.TranslationRecognizer(
    translation_config=translation_config,
    audio_config=audio_input
)

# =============================
# FUNÇÃO TTS → SALVA WAV
# =============================
import sounddevice as sd
import soundfile as sf

# def synthesize_to_vbcable(text: str):
#     speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
#     speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    
#     # Salva o arquivo temporário
#     temp_file = "output.wav"
#     audio_config = speechsdk.audio.AudioConfig(filename=temp_file)
#     synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
#     synthesizer.speak_text_async(text).get()

    # TOCA USANDO O ID NUMÉRICO (42 é o seu Voicemeeter Input)
    # data, fs = sf.read(temp_file)
    # # Tente o ID 42. Se der erro, tente o 54 (que também é Voicemeeter Input na sua lista)
    # sd.play(data, fs, device=42) 
    # sd.wait()

    # if os.path.exists(temp_file):
    #     data, fs = sf.read(temp_file)
    #     # 🔊 Agora sim, o som sai UMA ÚNICA VEZ apenas onde você quer (ID 42)
    #     sd.play(data, fs, device=42) 
    #     sd.wait() 
        
    #     try:
    #         os.remove(temp_file)
    #     except Exception as e:
    #         logging.error(f"Erro ao deletar arquivo temporário: {e}")

def synthesize_to_vbcable(text: str):
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    # 1. Configuramos o Azure para NÃO tocar som e NÃO salvar arquivo
    # Ele vai mandar os dados para um "Stream" na memória
    pull_stream = speechsdk.audio.PullAudioOutputStream()
    audio_config = speechsdk.audio.AudioOutputConfig(stream=pull_stream)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    # 2. Inicia a síntese
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        # 3. Pegamos os dados binários do áudio (PCM 16-bit 16kHz por padrão)
        audio_data = result.audio_data
        # Convertemos para o formato que o sounddevice entende (float32)
        import numpy as np
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        # 4. Toca direto no Voicemeeter (ID 42) sem salvar nada no PC!
        sd.play(audio_array, samplerate=16000, device=42)
        # sd.wait()


# def synthesize_to_vbcable(text: str):
#     speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
#     speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    
#     # Usando o ID que você encontrou no PowerShell
#     # O Azure no Windows muitas vezes exige o prefixo do driver
#     device_id = "VB-Audio Voicemeeter VAIO" 
    
#     # Se o nome acima falhar, a forma infalível de usar o ID ROOT\MEDIA\0001 é assim:
#     audio_config = speechsdk.audio.AudioOutputConfig(device_name=device_id)
    
#     synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)

#     # O .get() aqui espera o Azure ENVIAR os dados, mas não espera o áudio ACABAR de tocar.
#     # Isso reduz o delay drasticamente comparado ao sounddevice.
#     synthesizer.speak_text_async(text).get()
#     logging.info(f"🔊 Enviado direto para ROOT\\MEDIA\\0001: {text}")


# def synthesize_to_vbcable(text: str):
#     speech_config = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
#     speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
    
#     # 🚀 O SEGREDO DA LATÊNCIA ZERO:
#     # Em vez de salvar arquivo, o Azure joga o áudio num "buffer" de memória
#     synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

#     # Inicia a síntese e pega o resultado binário na hora
#     result = synthesizer.speak_text_async(text).get()
    
#     if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
#         import numpy as np
#         # Converte os bytes da Azure direto para ondas sonoras sem passar pelo HD
#         audio_array = np.frombuffer(result.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
#         # Toca no dispositivo 42 (Voicemeeter) ou no Sonar se você trocar
#         # IMPORTANTE: Sem o sd.wait(), o Python já libera o microfone para você falar a próxima frase
#         sd.play(audio_array, samplerate=16000, device=42)



# =============================
# CALLBACK DE RECONHECIMENTO
# =============================
def recognized(evt):
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        original = evt.result.text
        translated = evt.result.translations.get("en")

        if not translated:
            return

        logging.info(f"ORIGINAL (PT): {original}")
        logging.info(f"TRADUZIDO (EN): {translated}")

        # logging.info("Enviando áudio traduzido para o VB-Cable")
        synthesize_to_vbcable(translated)


# =============================
# START
# =============================
recognizer.recognized.connect(recognized)

logging.info("🎤 Fale em português. O áudio em inglês será gerado.")
recognizer.start_continuous_recognition()

try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    recognizer.stop_continuous_recognition()
    logging.info("Encerrado.")
