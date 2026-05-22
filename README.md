# WiDok<3
WiDok is a library for all files and code for the Wireless Dock project

## Installation
Clone the project in PyCharm and follow [this](https://medium.com/@andymule/micropython-in-pycharms-basic-setup-9169b497ec8a) tutorial to get MicroPython set up in the project.

## Usage
Install and configure MicroPython for your PCB. Connect and upload files for your PCB, open REPL in MicroPython Tools and soft reboot.

> [!TIP]
> Change the main.py file to use either Wand or Dock to auto-start preferred file at boot

Please add info to the `README.md` if you create a new file, or change / add to the functions of a file.

## File explanation
### Source folder
🔹 **WiDok-Wand**
  - Main file for the Wand
  - Defines and starts all sub-async tasks

🔹 **WiDok-Dock**
  - Main file for the Dock

### Source/Resources
🔹 **Battery_Sensing** (`Wand`)
  - Initialization and reading of ADC pin

🔹**Bluetooth_Protocol_** (`Wand`, `Dock`)
 - Bluetooth_Protocol_Wand: *Initializing, publishing and notifying of data over BLE*
 - Bluetooth_Protocol_Dock: *Unspecified*
 - To add characteristic ID's for new elements, genereate an unique UUID [here](https://www.uuidgenerator.net/)

🔹**IMU** (`Wand`)
 - Communication with the on board IMU, including the processing of said data

🔹 **LED_control** (`Wand`)
  - Control object for LED's, with necessary sub-functions
> **LED_control is universal** (Usable on both boards, with possibility for expansion)

🔹 **Tft_ldc_protocol** (`Dock`)
  - Undefined

🔹 **User_Signaling** (`Wand`, `Dock`)
  - Custom error handling

| **Error Code** | **Error Description** |
| :------------: | :-------------------: |
| `101` | *Unknown Error* |
| `102` | *Startup Error* |
| `103` | *Bluetooth Error* |
| `104` | *IMU Error* |
| `105` | *Battery Sensing Error* |
| `106` | *Temperature Error* |
| `107` | *Adressable LED Error* |

> **Thanks for the read<3** -Odaisen
