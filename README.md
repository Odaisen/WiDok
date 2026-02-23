# WiDok<3
WiDok is a library for all files and code for the Wireless Dock project

## Installation
Clone the project in PyCharm and follow [this](https://medium.com/@andymule/micropython-in-pycharms-basic-setup-9169b497ec8a) tutorial to get MicroPython set up in the project.

Then install neccessary libraries using:

```bash
pip install -r requirements.txt
```

## Usage
Configure run options and add MicroPython upload and execute for quick upload and testing to the ESP32.

Please also add info to the `README.md` if you create a new file, or change / add to the functions of a file.

> [!TIP]
> If you want the uploaded ESP32 files to auto-start at boot, change the WiDok-Wand / -Dock file name to main.py before uploading.

## File explanation
### Source folder
🔹 **WiDok-Wand**
  - Main file for the Wand

🔹 **WiDok-Dock**
    - Main file for the Dock

🔹 **Requirements**
  - File with all required libraries
  - Quick installation with:
```bash
pip install -r requirements.txt
```
  - Quick library updating with: (NOTE: DO NOT USE)
```bash
pip freeze > requirements.txt
```

### Resource folder
🔹**Bluetooth-Protocol**
 - All code for bluetooth communication between the Wand and the Dock (`Wand`, `Dock`)

🔹**IMU-DataCollector**
 - All code for the communication with the on board IMU (`Wand`)

🔹**Kalman-Filter**
 - Kalman-Filter for the IMU-Data (`Dock`)

> **Thanks for the read<3** -Odaisen
