Understood. Here's a complete **spec and script** to create a desktop notifier that listens for changes on the MQTT topic `homeassistant/binary_sensor/oref_alert/state`, connected to your **Mosquitto broker at `10.0.0.3:1883`**, using:

* **Username**: `daniel`
* **Password**: `MazalDagim1-`

---

### ✅ Specification for MQTT Alert Desktop Notifier

| Setting           | Value                                              |
| ----------------- | -------------------------------------------------- |
| **MQTT broker**   | `10.0.0.3` (port `1883`)                           |
| **Topic**         | `homeassistant/binary_sensor/oref_alert/state`     |
| **Trigger value** | `"ON"`                                             |
| **Action**        | Show Ubuntu desktop notification (`notify-send`)   |
| **Auth**          | Username/password auth (`daniel` / `MazalDagim1-`) |
| **Environment**   | Ubuntu 25.04 with KDE Plasma                       |

---

### ✅ Script: `alert-notify.sh`

```bash
#!/bin/bash

mosquitto_sub -h 10.0.0.3 -p 1883 \
  -u daniel \
  -P 'MazalDagim1-' \
  -t 'homeassistant/binary_sensor/oref_alert/state' | while read -r payload; do

    if [[ "$payload" == "\"on\"" || "$payload" == "on" || "$payload" == "\"ON\"" || "$payload" == "ON" ]]; then
        notify-send "Red Alert in Jerusalem" "Incoming missile warning! Take shelter."
    fi
done
```

---

### ✅ Installation & Use

1. Save as `~/alert-notify.sh`
2. Make it executable:

   ```bash
   chmod +x ~/alert-notify.sh
   ```
3. Run it
