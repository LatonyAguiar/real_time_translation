# import azure.cognitiveservices.speech as speechsdk
# import logging
# from config import AZURE_KEY, AZURE_REGION

# def create_translator(from_lang, to_lang):
#     config = speechsdk.translation.SpeechTranslationConfig(
#         subscription=AZURE_KEY,
#         region=AZURE_REGION
#     )

#     config.speech_recognition_language = from_lang
#     config.add_target_language(to_lang)

#     # Ajustes para a tradução não ficar travada (VAD)
#     config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "3000")
#     config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1000")

#     # Define a voz de saída baseada no idioma de destino
#     if to_lang == "en":
#         config.voice_name = "en-US-JennyNeural"
#     else:
#         config.voice_name = "pt-BR-FranciscaNeural"

#     logging.info(f"✅ Configuração Criada: {from_lang} -> {to_lang}")
#     return config
