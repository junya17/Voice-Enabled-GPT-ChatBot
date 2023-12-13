from openai import OpenAI
from pydub import AudioSegment
from pydub.playback import play
import requests
import json
import speech_recognition as sr


#Initialize the OpenAI client
client = OpenAI()

# Replace 'YOUR_API_KEY' with your actual API key from OpenWeatherMap
API_KEY = 'YOUR_API_KEY'
WEATHER_API_URL = 'http://api.openweathermap.org/data/2.5/weather'

def listen_from_microphone():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
        print("Audio captured, recognizing...")
    try:
        text = recognizer.recognize_google(audio)
        print("Recognized text:", text)
        return text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")

def get_current_weather(location, unit="imperial"):
    """Get the current weather in a given location using OpenWeatherMap API"""
    params = {
        'q': location,
        'appid': API_KEY,
        'units': unit
    }
    try:
        response = requests.get(WEATHER_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if "main" in data:
            weather_data = {
                "location": location,
                "temperature": data["main"].get("temp", "N/A"),
                "weather_condition": data["weather"][0]["main"] if "weather" in data and data["weather"] else "N/A",
                "humidity": data["main"].get("humidity", "N/A"),
                "wind_speed": data["wind"].get("speed", "N/A") if "wind" in data else "N/A",
                "pressure": data["main"].get("pressure", "N/A"),
                "visibility": data.get("visibility", "N/A")
            }
            return json.dumps(weather_data)
        else:
            return json.dumps({"location": location, "error": "Weather data not available"})
    except requests.exceptions.RequestException as e:
        return json.dumps({"location": location, "error": "API Request Failed", "message": str(e)})

def run_conversation():

    messages = []

    while True:
        user_input = listen_from_microphone()

        if user_input is None:
            print("No input received. Please try again.")
            continue

        if user_input.lower() == 'goodbye':  # End the conversation if user says 'goodbye'
            break

        messages.append({"role": "user", "content": user_input})
    
        tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["metric", "imperial"]},
                    },
                    "required": ["location"],
                },
            },
        }
        ]

        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            messages.append(response_message)
            for tool_call in tool_calls:
                function_args = json.loads(tool_call.function.arguments)
                function_response = get_current_weather(
                    location=function_args.get("location"),
                    unit=function_args.get("unit"),
                )
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": "get_current_weather",
                        "content": function_response,
                    }
                )
            second_response = client.chat.completions.create(
                model="gpt-3.5-turbo-1106",
                messages=messages,
            )
            second_response = second_response.choices[0].message.content

            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=second_response,
            )

            # response = response.stream_to_file("output.mp3")
            # print(second_response)
            # os.system('afplay output.mp3')
            temp_file = "temp_output_api.mp3"
            response.stream_to_file(temp_file)

            audio = AudioSegment.from_file(temp_file, format="mp3")
            play(audio)
            print(second_response)

            messages.append({"role": "assistant", "content": second_response})

        else:
            response_message = response.choices[0].message.content
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=response_message,
            )

            # response = response.stream_to_file("output.mp3")
            # print(response_message)
            # os.system('afplay output.mp3')
            temp_file = "temp_output_el.mp3"
            response.stream_to_file(temp_file)

            audio = AudioSegment.from_file(temp_file, format="mp3")
            play(audio)
            print(response_message)

            messages.append({"role": "assistant", "content": response_message})
        
    response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input="Good by",
            )
    
    # Say goodbye and end the conversation
    # response = response.stream_to_file("by.mp3")
    # print("Good by👋")
    # os.system('afplay by.mp3')

    temp_file = "temp_output_bye.mp3"
    response.stream_to_file(temp_file)

    audio = AudioSegment.from_file(temp_file, format="mp3")
    play(audio)
    print("Good by👋")

    return "Conversation ended."

print(run_conversation())
