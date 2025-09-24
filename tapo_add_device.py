import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import json, threading, time, ssl
from PyP100 import PyP100
import paho.mqtt.client as paho


class IoT:
    def __init__(self):
        self.devices = {}
        self.device_buttons = {}
        self.previous_status = {}

        self.root = tk.Tk()
        self.root.title("IOT")
        self.root.resizable(False, False)

        # Main frame
        self.main = ttk.Frame(self.root, padding=10)
        self.main.grid(row=0, column=0, sticky='NSEW')

        # Device content frame
        self.content = ttk.LabelFrame(self.root, text="ON/OFF BUTTON", padding=10)
        self.content.grid(row=0, column=0, padx=10, pady=10)

        # Add Device button
        self.add_btn = ttk.Button(self.root, text="➕ Add Device", command=self.add_device_popup)
        self.add_btn.grid(row=1, column=0, pady=10)

        # MQTT
        self.mac_address = "my/test/topic"
        self.client = self.client_param()

        self.load_devices()
        self.publish_device_count()

        # Start background status updater
        threading.Thread(target=self.device_info, daemon=True).start()

    def load_devices(self):
        """Load devices from JSON and create UI buttons."""
        with open("info.json", "r") as file:
            data = json.load(file)

        username = data["username"]
        password = data["password"]

        # Loop through all keys starting with "ip"
        for key, ip in [(k, v) for k, v in data.items() if k.startswith("ip")]:
            dev_num = key.replace("ip", "")
            dev_id = f"device{dev_num}"
            try:
                device = PyP100.P100(ip, username, password)
                device.handshake()
                device.login()
                self.devices[dev_id] = device
                self.previous_status[dev_id] = None
                self.create_device_ui(dev_id, ip)
            except Exception as e:
                print(f"Error loading {dev_id}: {e}")

    def create_device_ui(self, dev_id, ip):
        """Create UI elements for a new device."""
        frame = ttk.LabelFrame(self.content, text=ip, padding=10)
        frame.grid(row=len(self.device_buttons), column=0, padx=10, pady=5)

        btn = ttk.Button(frame, text="TURN ON", command=lambda d=dev_id: self.toggle_device(d))
        btn.grid(row=0, column=0, padx=10, pady=5)

        remove_btn = ttk.Button(
            frame,
            text="❌ Remove",
            command=lambda d=dev_id, i=ip, f=frame: self.remove_device(d, i, f),
        )
        remove_btn.grid(row=0, column=1, padx=10, pady=5)

        self.device_buttons[dev_id] = btn
        self.update_button_text(dev_id)

    def remove_device(self, dev_id, ip, frame):
        """Remove a device from JSON, UI, and internal list."""
        confirm = messagebox.askyesno("Remove Device", f"Are you sure you want to remove {ip}?")
        if not confirm:
            return

        # Remove from internal dictionaries
        if dev_id in self.devices:
            del self.devices[dev_id]

        if dev_id in self.device_buttons:
            del self.device_buttons[dev_id]

        if dev_id in self.previous_status:
            del self.previous_status[dev_id]

        # Destroy the UI frame
        frame.destroy()

        # Update JSON
        with open("info.json", "r") as file:
            data = json.load(file)

        dev_num = dev_id.replace("device", "")
        ip_key = f"ip{dev_num}"
        state_key = f"state{dev_num}"

        if ip_key in data:
            del data[ip_key]
        if state_key in data:
            del data[state_key]

        with open("info.json", "w") as file:
            json.dump(data, file, indent=4)

        # Publish updated count
        self.publish_device_count()

    def publish_device_count(self):
        """Publish total number of connected devices."""
        count = len(self.devices)
        payload = {"devices_connected": count}
        self.client.publish(self.mac_address + "/devices_count", payload=json.dumps(payload), qos=1)
        print("Published device count:", count)

    def toggle_device(self, dev_id):
        """Toggle ON/OFF state of a device and publish."""
        self.devices[dev_id].toggleState()
        self.update_button_text(dev_id)
        self.publish_state(dev_id)

    def update_button_text(self, dev_id):
        """Update ON/OFF button text."""
        status = self.get_status(self.devices[dev_id])
        self.device_buttons[dev_id].configure(text="TURN OFF" if status else "TURN ON")

    def get_status(self, device):
        """Check device status (ON/OFF)."""
        try:
            info = device.getDeviceInfo()
            return info["device_on"]
        except Exception:
            return False

    def publish_state(self, dev_id):
        """Publish the state of a given device to MQTT."""
        # Extract only the numeric part from dev_id like "device1" → "1"
        dev_num = ''.join(filter(str.isdigit, dev_id))
        state = "On" if self.get_status(self.devices[dev_id]) else "Off"
        payload = {"deviceId": f"Device {dev_num}", "state": state}
        self.client.publish(self.mac_address, payload=json.dumps(payload), qos=1)
        print("Published state:", payload)

    def add_device_popup(self):
        """Popup to add a new device."""
        ip = simpledialog.askstring("Add Device", "Enter device IP:")
        if not ip:
            return

        with open("info.json", "r") as file:
            data = json.load(file)

        username = data["username"]
        password = data["password"]

        # Find next available device number
        next_num = 1
        while f"ip{next_num}" in data:
            next_num += 1

        dev_id = f"device{next_num}"

        try:
            device = PyP100.P100(ip, username, password)
            device.handshake()
            device.login()
            self.devices[dev_id] = device
            self.previous_status[dev_id] = None

            # Save to JSON
            data[f"ip{next_num}"] = ip
            data[f"state{next_num}"] = "Off"
            with open("info.json", "w") as file:
                json.dump(data, file, indent=4)

            self.create_device_ui(dev_id, ip)
            self.publish_device_count()
            messagebox.showinfo("Success", f"Device {dev_id} added successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Could not add device: {e}")

    # ========== MQTT ==========
    def on_connect(self, client, userdata, flags, rc, properties=None):
        print("Connected with code %s." % rc)
        client.subscribe(self.mac_address, qos=1)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print("MQTT:", payload)

            device_id_str = payload.get("deviceId")  # e.g. "Device 1"
            state = payload.get("state")

            if not device_id_str or not state:
                return

            # Extract number part from "Device X"
            dev_num = ''.join(filter(str.isdigit, device_id_str))
            dev_id = f"device{dev_num}"

            if dev_id in self.devices:
                if state == "On":
                    self.devices[dev_id].turnOn()
                else:
                    self.devices[dev_id].turnOff()

                self.update_button_text(dev_id)

                # Save to JSON
                with open("info.json", "r") as file:
                    content = json.load(file)

                content[f"state{dev_num}"] = state

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
        client.connect("4f0992dbcdbb45729af2a31279d02983.s1.eu.hivemq.cloud", 8883)
        client.loop_start()
        return client

    # ========== Background device sync ==========
    def device_info(self):
        while True:
            try:
                with open("info.json", "r") as file:
                    content = json.load(file)

                # Iterate safely over a copy
                for dev_id, device in list(self.devices.items()):
                    status = self.get_status(device)

                    self.update_button_text(dev_id)

                    dev_num = dev_id.replace("device", "")
                    content[f"state{dev_num}"] = "On" if status else "Off"

                    if self.previous_status.get(dev_id) != status:
                        self.publish_state(dev_id)
                        self.previous_status[dev_id] = status

                with open("info.json", "w") as file:
                    json.dump(content, file, indent=4)

            except Exception as e:
                print("Error updating device info:", e)

            time.sleep(1)


if __name__ == "__main__":
    app = IoT()
    app.root.mainloop()
