import streamlit as st
import requests
import json
from openai import OpenAI

def get_current_weather(location, units="imperial"):
    api_key = st.secrets["OPENWEATHER_API_KEY"]
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={location}&appid={api_key}&units={units}"
    )
    response = requests.get(url)

    if response.status_code == 401:
        raise Exception("Authentication failed: Invalid OpenWeatherMap API key (401)")
    if response.status_code == 404:
        error_message = response.json().get("message", "City not found")
        raise Exception(f"404 error: {error_message}")

    data = response.json()
    return {
        "location":    location,
        "temperature": round(data["main"]["temp"], 2),
        "feels_like":  round(data["main"]["feels_like"], 2),
        "temp_min":    round(data["main"]["temp_min"], 2),
        "temp_max":    round(data["main"]["temp_max"], 2),
        "humidity":    round(data["main"]["humidity"], 2),
        "description": data["weather"][0]["description"],
        "units":       "°F" if units == "imperial" else "°C",
    }

weather_tool = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": (
            "Get the current weather for a given city. "
            "If no location is provided, default to Syracuse, NY, US."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, e.g. 'Syracuse, NY, US' or 'Lima, Peru'",
                }
            },
            "required": ["location"],
        },
    },
}


def lab5():
    st.title("🌤️ Lab 5 – What to Wear Bot")
    st.write("Enter a city name and I'll check the current weather, then suggest what to wear and fun outdoor activities!")

    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    city = st.text_input(
        "Enter a city (e.g. Syracuse, NY, US):",
        placeholder="Syracuse, NY, US",
    )

    if st.button("Get Advice") and city:
            with st.spinner("Checking the weather..."):
                try:
                    messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are a helpful weather-based fashion and activity advisor. "
                                "When the user provides a city, use the get_current_weather tool "
                                "to fetch current conditions, then give friendly advice on what to wear "
                                "and suggest appropriate outdoor activities. "
                                "If no city is given, use 'Syracuse, NY, US' as the default."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"What should I wear today in {city}? Also suggest some outdoor activities.",
                        },
                    ]

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=messages,
                        tools=[weather_tool],
                        tool_choice="auto",
                    )

                    response_message = response.choices[0].message

                    if response_message.tool_calls:
                        tool_call = response_message.tool_calls[0]
                        args = json.loads(tool_call.function.arguments)
                        location = args.get("location", "Syracuse, NY, US")
                        weather_data = get_current_weather(location)

                        st.subheader(f"📍 Current Weather in {weather_data['location']}")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Temperature", f"{weather_data['temperature']}{weather_data['units']}")
                        col2.metric("Feels Like", f"{weather_data['feels_like']}{weather_data['units']}")
                        col3.metric("Humidity", f"{weather_data['humidity']}%")
                        st.caption(f"Conditions: {weather_data['description'].title()} | Low: {weather_data['temp_min']}{weather_data['units']} | High: {weather_data['temp_max']}{weather_data['units']}")

                        messages.append(response_message)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(weather_data),
                        })

                        final_response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=messages,
                        )

                        advice = final_response.choices[0].message.content
                        st.subheader("👗 Clothing & Activity Suggestions")
                        st.write(advice)

                except Exception as e:
                    st.error(f"Something went wrong: {e}")

lab5()
