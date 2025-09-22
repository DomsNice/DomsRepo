import threading
import json
from PyP100 import PyP100
import time
import tkinter as tk
from tkinter import ttk
import paho.mqtt.client as paho
from paho import mqtt
import ssl


class IoT:
    def __init__(self):
        self.status = None
        self.status2 = None
        self.status3 = None
        self.previous_status = None
        self.previous_status_2 = None
        self.previous_status_3 = None

        self.root = tk.Tk()
        self.root.title("IOT")
        self.root.resizable(False, False)

        # Create the main frame
        self.main = ttk.Frame(self.root, padding=10)
        self.main.grid(row=0, column=0, sticky='NSEW')

        # open config file
        with open("info.json") as file:
            data = json.load(file)

        # Device IPs and credentials
        self.username = data["username"]
        self.password = data["password"]
        self.devices = {
            "device1": PyP100.P100(data["ip"], self.username, self.password),
            "device2": PyP100.P100(data["ip2"], self.username, self.password),
            "device3": PyP100.P100(data["ip3"], self.username, self.password)
        }

        # Authenticate all devices
        for dev in self.devices.values():
            dev.handshake()
            dev.login()

        # Restore states from config
        self.restore_device_state("device1", data.get("state"))
        self.restore_device_state("device2", data.get("state2"))
        self.restore_device_state("device3", data.get("state3"))

        # ==== Content ====
        content = ttk.LabelFrame(self.root, text="ON/OFF BUTTON", padding=10)
        content.grid(row=0, column=0, padx=10, pady=10)

        device1 = ttk.LabelFrame(content, text=data["ip"], padding=10)
        device1.grid(row=0, column=0, padx=10, pady=5)
        self.button1 = ttk.Button(device1, text="TURN ON", command=self.toggle_device1)
        self.button1.grid(row=0, column=0, padx=10, pady=5)

        device2 = ttk.LabelFrame(content, text=data["ip2"], padding=10)
        device2.grid(row=1, column=0, padx=10, pady=5)
        self.button2 = ttk.Button(device2, text="TURN ON", command=self.toggle_device2)
        self.button2.grid(row=0, column=0, padx=10, pady=5)

        device3 = ttk.LabelFrame(content, text=data["ip3"], padding=10)
        device3.grid(row=2, column=0, padx=10, pady=5)
        self.button3 = ttk.Button(device3, text="TURN ON", command=self.toggle_device3)
        self.button3.grid(row=0, column=0, padx=10, pady=5)

        self.mac_address = "my/test/topic"

        threading.Thread(target=self.device_info, daemon=True).start()

        # Initialize MQTT client
        self.client = self.client_param()

    def restore_device_state(self, device_key, state):
        """Restore device state from config file"""
        if state == "On":
            self.devices[device_key].turnOn()
        elif state == "Off":
            self.devices[device_key].turnOff()

    def get_status(self, device):
        """Helper to get ON/OFF status from device"""
        try:
            info = device.getDeviceInfo()
            return info["device_on"]
        except Exception:
            return False

    def toggle_device1(self):
        self.devices["device1"].toggleState()
        self.update_button_text()
        self.publish_state()

    def toggle_device2(self):
        self.devices["device2"].toggleState()
        self.update_button_text_2()
        self.publish_state_2()

    def toggle_device3(self):
        self.devices["device3"].toggleState()
        self.update_button_text_3()
        self.publish_state_3()

    def update_button_text(self):
        self.button1.configure(text='TURN OFF' if self.get_status(self.devices["device1"]) else 'TURN ON')

    def update_button_text_2(self):
        self.button2.configure(text='TURN OFF' if self.get_status(self.devices["device2"]) else 'TURN ON')

    def update_button_text_3(self):
        self.button3.configure(text='TURN OFF' if self.get_status(self.devices["device3"]) else 'TURN ON')

    def publish_state(self):
        state = "On" if self.get_status(self.devices["device1"]) else "Off"
        self.client.publish(self.mac_address, payload=json.dumps({"deviceId": "Device 1", "state": state}), qos=1)

    def publish_state_2(self):
        state2 = "On" if self.get_status(self.devices["device2"]) else "Off"
        self.client.publish(
            self.mac_address,
            payload=json.dumps({"deviceId": "Device 2", "state": state2}),
            qos=1
        )

    def publish_state_3(self):
        state3 = "On" if self.get_status(self.devices["device3"]) else "Off"
        self.client.publish(
            self.mac_address,
            payload=json.dumps({"deviceId": "Device 3", "state": state3}),
            qos=1
        )

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print("Connected with code %s." % rc)
        client.subscribe(self.mac_address, qos=0)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print("MQTT:", payload)

            device_id = payload.get("deviceId")
            state = payload.get("state")

            if device_id and state:
                if device_id == "Device 1":
                    self.devices["device1"].turnOn() if state == "On" else self.devices["device1"].turnOff()
                elif device_id == "Device 2":
                    self.devices["device2"].turnOn() if state == "On" else self.devices["device2"].turnOff()
                elif device_id == "Device 3":
                    self.devices["device3"].turnOn() if state == "On" else self.devices["device3"].turnOff()

            # Update UI
            self.update_button_text()
            self.update_button_text_2()
            self.update_button_text_3()

            # Save to info.json
            with open("info.json", "r") as file:
                content = json.load(file)

            if device_id == "Device 1":
                content["state"] = state
            elif device_id == "Device 2":
                content["state2"] = state
            elif device_id == "Device 3":
                content["state3"] = state

            with open("info.json", "w") as file:
                json.dump(content, file, indent=4)

        except Exception as e:
            print("Error processing MQTT:", e)

    def client_param(self):
        client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv311)
        client.on_connect = self.on_connect
        client.on_message = self.on_message

        client.tls_set(tls_version=ssl.PROTOCOL_TLS)
        client.username_pw_set("user1", "User1234")
        client.connect("5c1e782f3c924391aecb3b50c3b6316d.s1.eu.hivemq.cloud", 8883)
        client.loop_start()
        return client

    def device_info(self):
        while True:
            try:
                self.status = self.get_status(self.devices["device1"])
                self.status2 = self.get_status(self.devices["device2"])
                self.status3 = self.get_status(self.devices["device3"])

                if self.status != self.previous_status:
                    self.update_button_text()
                    self.publish_state()
                if self.status2 != self.previous_status_2:
                    self.update_button_text_2()
                    self.publish_state_2()
                if self.status3 != self.previous_status_3:
                    self.update_button_text_3()
                    self.publish_state_3()

                # Always update info.json
                with open("info.json", "r") as file:
                    content = json.load(file)
                content["state"] = "On" if self.status else "Off"
                content["state2"] = "On" if self.status2 else "Off"
                content["state3"] = "On" if self.status3 else "Off"
                with open("info.json", "w") as file:
                    json.dump(content, file, indent=4)

                self.previous_status = self.status
                self.previous_status_2 = self.status2
                self.previous_status_3 = self.status3

            except Exception as e:
                print("Error updating device info:", e)

            time.sleep(1)


if __name__ == "__main__":
    app = IoT()
    app.root.mainloop()
