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

    // Listen for incoming messages
    client.onMessageArrived = function (message) {
        const payload = JSON.parse(message.payloadString);
        console.log("Received:", payload);

        const deviceId = payload.deviceId;
        const state = payload.state;

        updateDeviceState(deviceId, state);
    };


    function onConnect() {
        console.log("Connected!");
        alert("Connected")
        client.subscribe("my/test/topic");
    }

    function updateDeviceState(deviceId, state) {
        const deviceBox = document.querySelector(`[data-device="${deviceId}"]`);

        if (deviceBox) {
            const indicator = deviceBox.querySelector('.indicator');
            const status = deviceBox.querySelector('.status');

            // Update the device state visually
            if (state === 'On') {
                indicator.classList.add('on');
                status.textContent = 'Device is ON';
            } else if (state === 'Off') {
                indicator.classList.remove('on');
                status.textContent = 'Device is OFF';
            }
        }
    }

    // Function to update state for all devices
    function updateAllDevicesState(state) {
        // Find all devices (elements with data-device attribute)
        const deviceBoxes = document.querySelectorAll('[data-device]');

        deviceBoxes.forEach(deviceBox => {
            const indicator = deviceBox.querySelector('.indicator');
            const status = deviceBox.querySelector('.status');

            // Update the state for each device based on the received payload
            if (state === 'On') {
                indicator.classList.add('on');
                status.textContent = 'Device is ON';
            } else {
                indicator.classList.remove('on');
                status.textContent = 'Device is OFF';
            }
        });
    }

    // Device button logic
    const buttons = document.querySelectorAll('.toggle-button');
    const notification = document.getElementById('notification');
    let notificationTimeout;

    buttons.forEach(button => {
        button.addEventListener('click', () => {
            const deviceBox = button.parentElement;
            const indicator = deviceBox.querySelector('.indicator');
            const status = deviceBox.querySelector('.status');
            const deviceName = deviceBox.getAttribute('data-device');
            const isOn = indicator.classList.contains('on');
            const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            let message = '';
            let mqtt_message = {};

            if (isOn) {
                indicator.classList.remove('on');
                status.textContent = 'Device is OFF';
                button.textContent = 'Turn ON';
                message = `${deviceName} is Off`;
                mqtt_message = { "deviceId": deviceName, "state": "Off" };
            } else {
                indicator.classList.add('on');
                status.textContent = 'Device is ON';
                button.textContent = 'Turn OFF';
                message = `${deviceName} is On`;
                mqtt_message = { "deviceId": deviceName, "state": "On" };
            }

            client.send("my/test/topic", JSON.stringify(mqtt_message)); // Send updated state to the topic
            showNotification(message);
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
