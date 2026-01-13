# 📘 README.md — Real-Time Speech Translation (PT ⟷ EN)

Sistema de tradução de voz em tempo real usando Azure Speech Translation, pensado para entrevistas, reuniões e calls internacionais, funcionando com Google Meet, Microsoft Teams e Zoom, sem que a outra parte perceba.

## 🎯 Objetivo

Permitir que você:

* 🎤 Fale em português → o gringo escuta em inglês
* 🎧 Escute o gringo em inglês → você ouve em português
* ⏱ Em tempo real
* 🚫 Sem eco
* 🚫 Sem loop
* 💰 Paga somente quando usar

## 🧠 Como funciona (visão geral)

```
Seu Microfone
   ↓
Azure Speech (PT → EN)
   ↓
VB-Audio Input → Meet / Teams / Zoom

Meet / Teams / Zoom
   ↓
VB-Audio Output
   ↓
Azure Speech (EN → PT)
   ↓
Seu Fone
```

## 📦 Requisitos

### Sistema

* Windows 10 ou 11
* Python 3.10+
* Conta Azure com Speech Service ativo
* VB-Audio Virtual Cable instalado

### Python

* `pip`
* `virtualenv` (opcional, mas recomendado)

## 📁 Estrutura do Projeto

```
real_time_translation/
│
├── .env
├── README.md
├── requirements.txt
├── config.py
├── audio_devices.py
├── translator.py
├── main.py
└── logs/
    └── app.log
```

## 🔧 Instalação

### 1️⃣ Clone ou crie a pasta do projeto

```bash
mkdir real_time_translation
cd real_time_translation
```

### 2️⃣ Crie o ambiente virtual (opcional, recomendado)

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3️⃣ Instale as dependências

```bash
pip install -r requirements.txt
```

## 🔐 Configuração do Azure

### 4️⃣ Crie o arquivo `.env`

```
AZURE_SPEECH_KEY=SUA_API_KEY_AQUI
AZURE_SPEECH_REGION=eastus
```

⚠️ Nunca commite esse arquivo em repositório público

## 🎧 Configuração de Áudio

### 5️⃣ Liste os dispositivos de áudio

```bash
python audio_devices.py
```

Você verá algo como:

```
1  - Microfone Realtek
2  - VB-Audio Output
11 - VB-Audio Input
5  - Headset
```

### 6️⃣ Ajuste os IDs em `config.py`

```python
MIC_ID = 1          # Seu microfone
VB_INPUT_ID = 11    # Vai para Meet / Teams
VB_OUTPUT_ID = 2    # Áudio do Meet
SPEAKER_ID = 5      # Seu fone
```

## ▶️ Como Rodar

### 7️⃣ Inicie o sistema

```bash
python main.py
```

Você verá logs como:

```
🚀 SISTEMA DE TRADUÇÃO INICIADO
🎤 Rodando: pt-BR → en
🎧 Rodando: en-US → pt
```

## 🎙️ Configuração no Meet / Teams / Zoom

**Microfone**

```
VB-Audio Input
```

**Alto-falante**

```
VB-Audio Output
```

⚠️ Nunca use seu microfone ou fone direto no Meet, senão gera loop.

## 📜 Logs

Os logs ficam em:

```
logs/app.log
```

Incluem:

* Texto reconhecido
* Tradução
* Erros
* Status do sistema

## 💰 Custos (Azure Speech)

* 💵 ~ US$1 por hora de call
* 🎁 US$200 de crédito gratuito
* ❌ Sem mensalidade
* ❌ Só paga quando estiver rodando

Uma entrevista de 1h custa menos que um café.

## 🧠 Boas Práticas

✅ Use fone (nunca caixa de som)  
✅ Feche outros apps que usam microfone  
✅ Teste antes da entrevista  
✅ Fale frases curtas (menos latência)

## ❌ Problemas Comuns

### ❓ Eco

➡️ Conferir se o Meet NÃO está usando seu mic real

### ❓ Nada acontece

➡️ Verifique:

* API Key
* Region
* IDs de áudio
* Créditos Azure

### ❓ Latência alta

➡️ Normal até ~1s  
➡️ Muito menor que modelo local

## 🚀 Próximos Upgrades (opcional)

* UI gráfica
* Push-to-talk
* Detecção automática de silêncio
* Gravação da call
* Troca dinâmica de idioma


## 🧠 Conclusão

Esse sistema existe pra você não perder vaga por idioma. E sim — muita gente já usa isso, só não fala.

Se quiser:

* otimizar
* simplificar
* baratear ainda mais
* ou deixar invisível nível ninja

👉 só falar.
