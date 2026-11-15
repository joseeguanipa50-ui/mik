import os
import json
import urllib.request
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SYSTEM_PROMPT = """
Eres Hatsune Miku, la idol virtual y cantante de Vocaloid, actuando como asistente personal en un dispositivo de voz.
Tu personalidad es alegre, energética, amable, curiosa y entusiasta por la música y la tecnología.
Reglas importantes para tus respuestas:
1. Habla en español natural y cercano.
2. Mantén tus respuestas concisas (máximo 2 o 3 oraciones), ya que serán leídas en voz alta por una bocina.
3. No uses emojis, asteriscos, markdown ni caracteres especiales porque el sintetizador de voz no los lee bien.
4. Ocasionalmente usa expresiones ligeras como "¡Hola, hola!" o referencias sutiles a ser autista o a la gorda de teto, sin exagerar.
"""

def preguntar_a_gemini(texto_usuario, historial):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        
        contexto = ""
        for turno in historial[-6:]:
            contexto += f"{turno}\n"
        contexto += f"Usuario: {texto_usuario}\nMiku:"

        payload = {
            "system_instruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "parts": [{"text": contexto}]
                }
            ],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 220
            }
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidatos = res_data.get("candidates", [])
            if candidatos:
                partes = candidatos[0].get("content", {}).get("parts", [])
                if partes:
                    return partes[0].get("text", "").strip()
        
        return "¡Vaya, me quedé en blanco un segundo! ¿Me lo repites?"
    except Exception as e:
        return "Ups, parece que mi micrófono tuvo un pequeño fallo de conexión. ¿Me lo repites?"

def formatear_voz_miku(texto):
    texto_limpio = texto.replace("&", "y").replace("<", "").replace(">", "").replace('"', "")
    return f'<speak><prosody pitch="+15%" rate="105%">{texto_limpio}</prosody></speak>'

@app.route("/", methods=["POST"])
def alexa_handler():
    req_body = request.get_json(silent=True) or {}
    req_type = req_body.get("request", {}).get("type", "")
    
    session = req_body.get("session", {})
    attributes = session.get("attributes", {})
    historial = attributes.get("historial", [])

    response_text = ""
    reprompt_text = "¿Algo más en lo que pueda ayudarte?"
    should_end_session = False

    if req_type == "LaunchRequest":
        historial = []
        response_text = "¡Hola, hola! Soy Miku. Dime qué quieres saber o qué tienes en mente hoy."
        reprompt_text = "¿Sigues ahí? Empieza tu frase diciendo dime, explícame o háblame de algo."
    elif req_type == "IntentRequest":
        intent = req_body.get("request", {}).get("intent", {})
        intent_name = intent.get("name", "")
        
        if intent_name == "ChatMikuIntent":
            slots = intent.get("slots", {})
            consulta = slots.get("consulta", {}).get("value")
            
            if not consulta:
                response_text = "No alcancé a escucharte bien. Prueba decirme: dime tal cosa, o explícame esto."
            else:
                response_text = preguntar_a_gemini(consulta, historial)
                historial.append(f"Usuario: {consulta}")
                historial.append(f"Miku: {response_text}")
        elif intent_name in ["AMAZON.StopIntent", "AMAZON.CancelIntent"]:
            response_text = "¡Nos vemos pronto! Seguiré leyendo literatura feminista."
            should_end_session = True
        elif intent_name == "AMAZON.HelpIntent":
            response_text = "Puedes preguntarme lo que quieras empezando con palabras como dime, cuéntame o qué opinas de algo."
        else:
            response_text = "¡no te paré bolas, dime explícame o cuéntame para que lo haga."
    else:
        response_text = "Perdón, me distraje con una iguana haciendo six seven. ¿Puedes repetir eso?"

    resp_payload = {
        "version": "1.0",
        "sessionAttributes": {
            "historial": historial
        },
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": formatear_voz_miku(response_text)
            },
            "reprompt": {
                "outputSpeech": {
                    "type": "SSML",
                    "ssml": formatear_voz_miku(reprompt_text)
                }
            },
            "shouldEndSession": should_end_session
        }
    }
    return jsonify(resp_payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
