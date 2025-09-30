document.addEventListener('DOMContentLoaded', () => {
    const clientID = "webclient_" + parseInt(Math.random() * 1000000, 10);

    const client = new Paho.Client(
        "ad13c9d3eb1a4c53b4c7cffe6d4e3fad.s1.eu.hivemq.cloud",
        Number(8884),
        "/mqtt",
        clientID
    );

    client.connect({
        useSSL: true,
        userName: "MQTTuser",
        password: "MQ77u$er",
        onSuccess: onConnect,
        onFailure: (err) => console.error("Connection failed", err)
    });	

    client.onMessageArrived = function (message) {
        try {
            const payload = JSON.parse(message.payloadString);
            if (payload.deviceId && payload.state) {
                updateDeviceState(payload.deviceId, payload.state, false); 
                saveDeviceState(payload.deviceId, payload.state); // persist state
            }
        } catch (e) {
            console.error("Invalid message format", e);
        }
    };

    function onConnect() {
        client.subscribe("my/test/topic");
        showNotification("✅ Connected to MQTT broker");

        // Re-apply saved states after reconnect
        const savedDevices = JSON.parse(localStorage.getItem('devices') || "[]");
        savedDevices.forEach(d => {
            updateDeviceState(d.deviceId, d.state, false);
        });
    }

    function updateDeviceState(deviceId, state, shouldPublish = true) {
        const deviceBox = document.querySelector(`[data-device="${deviceId}"]`);
        if (deviceBox) {
            const indicator = deviceBox.querySelector('.indicator');
            const status = deviceBox.querySelector('.status');
            const button = deviceBox.querySelector('.toggle-button');

            if (state === 'On') {
                indicator.classList.add('on');
                status.textContent = 'Device is ON';
                button.textContent = 'Turn OFF';
            } else {
                indicator.classList.remove('on');
                status.textContent = 'Device is OFF';
                button.textContent = 'Turn ON';
            }

            if (shouldPublish) {
                const mqtt_message = { deviceId, state };
                client.send("my/test/topic", JSON.stringify(mqtt_message));
                saveDeviceState(deviceId, state); // persist state change
            }
        }
    }

    // Save device state to localStorage
    function saveDeviceState(deviceId, state) {
        let savedDevices = JSON.parse(localStorage.getItem('devices') || "[]");
        const index = savedDevices.findIndex(d => d.deviceId === deviceId);
        if (index >= 0) {
            savedDevices[index].state = state;
        } else {
            savedDevices.push({ deviceId, state });
        }
        localStorage.setItem('devices', JSON.stringify(savedDevices));
    }

    // Notification
    const notification = document.getElementById('notification');
    let notificationTimeout;
    function showNotification(message) {
        notification.textContent = message;
        notification.classList.remove('hidden');
        notification.classList.add('show');

        clearTimeout(notificationTimeout);
        notificationTimeout = setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.classList.add('hidden'), 500);
        }, 3000);
    }

    // Attach toggle handler
    function attachToggleHandler(button) {
        button.addEventListener('click', () => {
            const deviceBox = button.closest('.device-box');
            const deviceId = deviceBox.getAttribute('data-device');
            const isOn = deviceBox.querySelector('.indicator').classList.contains('on');
            const newState = isOn ? "Off" : "On";
            updateDeviceState(deviceId, newState, true);
            showNotification(`${deviceId} turned ${newState}`);
        });
    }

    // Attach to existing buttons
    document.querySelectorAll('.toggle-button').forEach(attachToggleHandler);

    // Add Device button
    const addDeviceBtn = document.getElementById('addDeviceBtn');
    let deviceCount = document.querySelectorAll('.device-box').length;

    addDeviceBtn.addEventListener('click', () => {
        deviceCount++;
        const newDeviceId = `Device ${deviceCount}`;
        createDeviceBox(newDeviceId, "Off", true);
    });

    // Create device (with fade-in + save option)
    function createDeviceBox(deviceId, initialState, save = false) {
        const devicesContainer = document.getElementById('devices');
        const deviceBox = document.createElement('div');
        deviceBox.classList.add('device-box', 'fade-in');
        deviceBox.setAttribute('data-device', deviceId);
        deviceBox.innerHTML = `
            <h2>${deviceId.toUpperCase()}</h2>
            <div class="indicator"></div>
            <p class="status">Device is OFF</p>
            <button class="toggle-button">Turn ON</button>
        `;
        devicesContainer.appendChild(deviceBox);

        requestAnimationFrame(() => deviceBox.classList.add('show'));

        const button = deviceBox.querySelector('.toggle-button');
        attachToggleHandler(button);

        // Apply initial state
        updateDeviceState(deviceId, initialState, false);

        if (save) {
            saveDeviceState(deviceId, initialState);
            showNotification(`${deviceId} added`);
        }
    }

    // Restore devices + state from localStorage
    const savedDevices = JSON.parse(localStorage.getItem('devices') || "[]");
    savedDevices.forEach(d => {
        if (!document.querySelector(`[data-device="${d.deviceId}"]`)) {
            createDeviceBox(d.deviceId, d.state, false);
            deviceCount++;
        }
    });
});







