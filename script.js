document.addEventListener('DOMContentLoaded', () => {
    const clientID = "webclient_" + parseInt(Math.random() * 1000000, 10);

    const client = new Paho.Client(
        "5c1e782f3c924391aecb3b50c3b6316d.s1.eu.hivemq.cloud",
        Number(8884),
        "/mqtt",
        clientID
    );

    client.connect({
        useSSL: true,
        userName: "user1",
        password: "User1234",
        onSuccess: onConnect,
        onFailure: (err) => console.error("Connection failed", err)
    });

    // Handle incoming messages
    client.onMessageArrived = function (message) {
        try {
            const payload = JSON.parse(message.payloadString);
            console.log("Received:", payload);

            if (payload.deviceId && payload.state) {
                updateDeviceState(payload.deviceId, payload.state, false); // false = don’t re-publish
            }
        } catch (e) {
            console.error("Invalid message format", e);
        }
    };

    function onConnect() {
        console.log("Connected!");
        client.subscribe("my/test/topic");
        showNotification("✅ Connected to MQTT broker");
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

            // Only publish if change came from UI
            if (shouldPublish) {
                const mqtt_message = { deviceId, state };
                client.send("my/test/topic", JSON.stringify(mqtt_message));
            }
        }
    }

    // Handle button clicks
    const buttons = document.querySelectorAll('.toggle-button');
    const notification = document.getElementById('notification');
    let notificationTimeout;

    buttons.forEach(button => {
        button.addEventListener('click', () => {
            const deviceBox = button.closest('.device-box');
            const deviceId = deviceBox.getAttribute('data-device');
            const isOn = deviceBox.querySelector('.indicator').classList.contains('on');

            const newState = isOn ? "Off" : "On";
            updateDeviceState(deviceId, newState, true);

            showNotification(`${deviceId} turned ${newState}`);
        });
    });

    function showNotification(message) {
        notification.textContent = message;
        notification.classList.remove('hidden');
        notification.classList.add('show');

        clearTimeout(notificationTimeout);
        notificationTimeout = setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.classList.add('hidden');
            }, 500);
        }, 3000);
    }
});
