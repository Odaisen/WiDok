This is the README file for the WiDok GitHub project, this includes all code and eventually all Altium files for both the Dock and Wand.

Add code / file explanation below:
---
Main: (IMPORTANT NOTE: If you want them to auto-start at boot, you have to change their name to main.py before uploading)

WiDok-Wand
  -Main file for the Wand

WiDok-Dock
  -Main file for the Dock

Requirements
  -File with all required libraries
  -Quick installation with: pip install -r requirements.txt
  -Quick library adding with: pip freeze > requirements.txt (DO NOT RUN)

---
Resources:
Bluetooth-Protocol
  -All code for bluetooth communication between the Wand and the Dock

IMU-DataCollector
  -All code for the communication with the on board IMU (Wand)

Kalman-Filter
  -Kalman-Filter for the IMU data (Dock)
