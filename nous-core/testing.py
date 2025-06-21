import requests
import json
import os

# Set up environment variables or hardcode for testing
PAYLOAD_CMS_LESSON_URL = os.getenv("PAYLOAD_CMS_LESSON_URL", "http://localhost:3000/api/lessons")
PAYLOAD_CMS_TOKEN = os.getenv("PAYLOAD_CMS_TOKEN")

# Use the provided lesson_data for testing
lesson_data = {
    "title": "Introduction to Signals and Systems",
    "content": {
        "root": {
            "children": [
                {
                    "type": "upload-local-audio",
                    "version": 3,
                    "format": "",
                    "id": "audio_20250606142857",
                    "fields": None,
                    "relationTo": "media-local",
                    "value": {
                        "local_path": "media\\narration_20250606152212.mp3",
                        "alt": "audio_20250606142857",
                        "filename": "narration_20250606152212.mp3",
                        "mimeType": "audio/mp3",
                        "filesize": 2537568
                    }
                },
                {"type": "heading", "tag": "h1", "children": [{"text": "INTRODUCTION TO SIGNALS AND SYSTEMS", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Course: CPE113", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Subject: DIGITAL SIGNAL PROCESSING", "type": "text"}], "indent": 0},
                {"type": "heading", "tag": "h2", "children": [{"text": "Signal", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [
                    {"text": "A ", "type": "text"},
                    {"text": "signal", "type": "text", "format": "bold"},
                    {"text": " is defined as any physical quantity that varies with time, space, or any other independent variable or variables.", "type": "text"}
                ], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Mathematically, we describe a signal as a function of one or more independent variables.", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Examples:", "type": "text"}], "indent": 0},
                {"type": "list", "listType": "unordered", "children": [
                    {"type": "listitem", "children": [{"text": "s(t) = 2t² + 3t - 2 (Single-Variable)", "type": "text"}], "indent": 0},
                    {"type": "listitem", "children": [{"text": "u(x, y) = x²y – 3x + 2y (Multi-Variable)", "type": "text"}], "indent": 0}
                ], "indent": 0},
                {"type": "heading", "tag": "h2", "children": [{"text": "Representing Complex Signals", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Some signals are too complicated to be represented by simple functions, such as speech signals.", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "These complex signals may be represented to a high degree of accuracy as a sum of several sinusoids of different amplitudes and frequencies.", "type": "text"}], "indent": 0},
                {"type": "heading", "tag": "h2", "children": [{"text": "Signal Source", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Signal generation is usually associated with a system that responds to a stimulus or force.", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [
                    {"text": "In a speech signal, the system consists of the vocal cords and the vocal tract (vocal cavity). The stimulus in combination with this system is called a ", "type": "text"},
                    {"text": "signal source", "type": "text", "format": "bold"},
                    {"text": ".", "type": "text"}
                ], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Examples of signal sources include speech sources, image sources, and various other types.", "type": "text"}], "indent": 0},
                {"type": "heading", "tag": "h2", "children": [{"text": "System", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [
                    {"text": "A ", "type": "text"},
                    {"text": "system", "type": "text", "format": "bold"},
                    {"text": " may also be defined as a physical device that performs an operation on a signal.", "type": "text"}
                ], "indent": 0},
                {"type": "paragraph", "children": [{"text": "For example, a filter used to reduce noise and interference corrupting a desired information-bearing signal is called a system. This filter performs operations on the signal to reduce noise.", "type": "text"}], "indent": 0},
                {"type": "heading", "tag": "h2", "children": [{"text": "Signal Processing", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [
                    {"text": "Signal processing", "type": "text", "format": "bold"},
                    {"text": " is a method of extracting information from the signal, which depends on the type of signal and the nature of information it carries.", "type": "text"}
                ], "indent": 0},
                {"type": "paragraph", "children": [{"text": "It is concerned with representing signals in mathematical terms and extracting information by carrying out algorithmic operations on the signal.", "type": "text"}], "indent": 0},
                {"type": "heading", "tag": "h2", "children": [{"text": "Analog Signal Processing", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Most signals in science and engineering are analog in nature. Analog signal processing involves processing the signal directly in its analog form.", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "In this method, both the input signal and the output signal remain in analog form.", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Conceptual Flow: Analog Input Signal → Analog Signal Processor → Analog Output Signal", "type": "text"}], "indent": 0},
                {"type": "heading", "tag": "h2", "children": [{"text": "Digital Signal Processing", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Digital signal processing provides an alternative method for processing analog signals.", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "To process signals digitally, an interface called an analog-to-digital (A/D) converter is needed between the analog signal and the digital processor. The A/D converter's output is a digital signal, suitable as input for the digital processor.", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "In applications where the digital output needs to be presented to the user in analog form (e.g., speech communications), another interface is required: a digital-to-analog (D/A) converter. This converts the digital output back to an analog signal.", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Conceptual Flow: Analog Input Signal → A/D Converter → Digital Input Signal → Digital Signal Processor → Digital Output Signal → D/A Converter → Analog Output Signal", "type": "text"}], "indent": 0},
                {"type": "heading", "tag": "h2", "children": [{"text": "Advantages of Digital over Analog Processing", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Digital signal processing of an analog signal is often preferable to direct analog processing for several reasons:", "type": "text"}], "indent": 0},
                {"type": "list", "listType": "unordered", "children": [
                    {"type": "listitem", "children": [{"text": "Digital circuits are less sensitive to variations in component values, temperature, ageing, and other external parameters because their operation does not depend on precise analog signal values.", "type": "text"}], "indent": 0},
                    {"type": "listitem", "children": [{"text": "A digital programmable system offers flexibility in reconfiguring signal processing operations simply by changing the program.", "type": "text"}], "indent": 0},
                    {"type": "listitem", "children": [{"text": "Digital systems provide much better control over accuracy requirements.", "type": "text"}], "indent": 0},
                    {"type": "listitem", "children": [{"text": "Digital signals are easily stored on magnetic or other digital media, making them transportable and allowing for off-line processing in remote laboratories.", "type": "text"}], "indent": 0},
                    {"type": "listitem", "children": [{"text": "Digital signal processing enables the implementation of more sophisticated signal processing algorithms.", "type": "text"}], "indent": 0},
                    {"type": "listitem", "children": [{"text": "In some cases, a digital implementation of a signal processing system can be cheaper than its analog counterpart.", "type": "text"}], "indent": 0}
                ], "indent": 0},
                {"type": "heading", "tag": "h2", "children": [{"text": "Drawbacks of Digital Processing", "type": "text"}], "indent": 0},
                {"type": "paragraph", "children": [{"text": "Despite its advantages, digital processing also has some drawbacks:", "type": "text"}], "indent": 0},
                {"type": "list", "listType": "unordered", "children": [
                    {"type": "listitem", "children": [{"text": "It requires 'pre' and 'post' processing devices, such as analog-to-digital (A/D) and digital-to-analog (D/A) converters, and associated reconstruction filters.", "type": "text"}], "indent": 0},
                    {"type": "listitem", "children": [{"text": "Digital techniques can suffer from frequency limitations.", "type": "text"}], "indent": 0},
                    {"type": "listitem", "children": [{"text": "Digital systems are constructed using active devices that consume power, whereas analog processing algorithms can often be implemented using passive devices that do not consume power.", "type": "text"}], "indent": 0}
                ], "indent": 0},
                {"type": "heading", "tag": "h3", "children": [{"text": "END OF PRESENTATION", "type": "text"}], "indent": 0}
            ],
            "direction": "ltr",
            "format": "",
            "indent": 0,
            "type": "root",
            "version": 1
        }
    },
    "published": True,
    "course": {"id": 3}
}

headers = {"Content-Type": "application/json"}
if PAYLOAD_CMS_TOKEN:
    headers["Authorization"] = f"Bearer {PAYLOAD_CMS_TOKEN}"

response = requests.post(PAYLOAD_CMS_LESSON_URL, headers=headers, json=lesson_data)
print("Status code:", response.status_code)
try:
    print("Response:", response.json())
except Exception:
    print("Raw response:", response.text)
