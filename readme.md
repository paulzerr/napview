# NAPVIEW - An autoscoring visualizer for real-time sleep experiments.

[Read the manual here: napview.netlify.app](https://napview.netlify.app/)

NAPVIEW is a user-friendly software for automatic real-time sleep stage classification in the sleep lab. It provides a real-time interface to deep learning machine learning algorithm output. It connects to live EEG data, runs automated sleep stage classification using powerful machine learning tools, and displays stage probabilities and signal features. NAPVIEW runs independently of existing lab setups and is intended to make the lives of researchers easier during live monitoring at night.

At present NAPVIEW directly supports BrainVision and OpenBCI EEG hardware, but any EEG system that allows real-time signal streaming can be connected through a labstreaminglayer (LSL) connector.

## Installation

### Option 1: [Download NAPVIEW installer (Windows)](https://github.com/paulzerr/napview/releases/latest/download/NAPVIEW_installer.exe)

The easiest way to use napview on Windows is to download the portable self-extracting installer.

**Note:** due to the restrictive environment of Windows, you may see a "Search on app store" popup window. Click "No". You may also see the blue Smartscreen warning. In that case click "More info" and then "run anyway". You can also right-click `NAPVIEW.exe`, go to Properties and tick the box "Unblock". Should this fail, try installing via the standalone archive or pip (see below).

### Option 2: [Download NAPVIEW standalone (Windows)](https://github.com/paulzerr/napview/releases/latest/download/NAPVIEW_installer.zip)

Download the zip archive, extract it to your preferred location, then double click `run_napview.bat` to start NAPVIEW. This installation method can be useful on systems without admin priviledges.

### Option 3: Install as Python package

First install e.g. [Miniconda](https://www.anaconda.com/download/success).

**Windows:**

```bash
conda create -n napview-env python=3.11 -y
conda activate napview-env
pip install napview
```

**macOS/Linux:**

```bash
conda create -n napview-env python=3.11 -y
conda activate napview-env
pip install napview
```

**Launch NAPVIEW:**

```bash
conda activate napview-env
napview
```

**Note:** on first run, NAPVIEW may download model weights via the NIDRA backend.

## GUI Guide

### Graphical user interface (GUI)

NAPVIEW launches a local control panel in your browser and opens a second tab for the real-time visualizer. The default control URL is `http://127.0.0.1:8145`. If that port is unavailable, NAPVIEW will pick the next free port. The browser window should open automatically.

### Walkthrough

#### Step 1: Start NAPVIEW

Start `NAPVIEW.exe` or run `napview` in a terminal or command prompt. A browser window opens with the control panel.

#### Step 2: Set data directory and record name

Use the Data directory selector to choose where session files and outputs are stored. The default location is your user data directory under `napview/data`.

#### Step 3: Select data source

- **Playback recording (simulator):** use the integrated example recording or select a local EDF file to simulate a live stream. The file is copied into the session data directory.
- **BrainVision:** enter the IP and RDA port of the EEG acquisition PC. On Windows you can find the IP by opening a command prompt (`CTRL+R`, then type `cmd`, press Enter. Next, type `ipconfig`, press Enter, and look for an entry under "Ethernet adapter" or "Wireless LAN adapter Wi-Fi" if using Wi-Fi labeled "IPv4 Address"). The number shown next to IPv4 Address is the IP address of the EEG acquisition PC. The port is typically `51234`.
- **OpenBCI:** choose a board type and port (if required). Use Synthetic to test without hardware.
- **Custom LSL stream:** provide the LSL stream name (default in config is `napview_EEG_stream`).
- **ZMax:** currently not implemented.

#### Step 4: Select the sleep staging model

Choose the sleep staging model. Currently only `U-Sleep` is available, which is a reliable state-of-the-art autoscorer.

#### Step 5: Optional settings

- **Analysis parameters:** e.g. adjust epoch length. This is currently not implemented and 30s epochs will always be used.
- **Channel configuration:** select EEG channels to use. This is optional, as NAPVIEW will automatically detect channel type and will skip noisy or empty channels. During scoring all combinations between valid EEG and EOG channels are being used and scored individually. The final score is then determined by majority vote.

#### Step 6: Start streaming

Click **START napview**. A new tab opens with the real-time visualizer, typically at `http://127.0.0.1:8245`. Sleep stage probabilities stabilize after several minutes of data. Less than 5 minutes of data will likely not result in reliable estimates. A maximum of 15 minutes of past data will be used.

#### Step 7: Shutdown and save

Once the experiment session is finished, click **SHUTDOWN and save** to stop the session and write outputs.

## Notes

- NAPVIEW expects a continuous EEG stream with channel names available from the stream metadata.
- Use the Simulator to test the systemwith a static EDF file.
- For BrainVision, make sure the RDA plugin is enabled and configured correctly.
- For custom LSL streams, make sure the stream type is EEG and the name matches the value in the GUI.
- It is recommended that you test the system first with the Simulator, then with an EEG amp connected without a participant, and finally with an awake participant. If everything works as expected you are now prepared to use NAPVIEW during an overnight session.

## Model Validation

NAPVIEW uses the NIDRA backend for real-time scoring. The default staging model is U-Sleep, which has been validated in large multi-center datasets. For detailed performance metrics, refer to the original U-Sleep publication:

[U-Sleep: resilient high-frequency sleep staging (Perslev et al., 2021)](https://www.nature.com/articles/s41746-021-00440-5)

## FAQ & Troubleshooting

### GUI issues

**Q: The GUI did not open.**  
A: Check the terminal output for the correct URL, normally `http://127.0.0.1:8145`, and enter it manually in the browser. Otherwise check the logs, which should be in your user directory, e.g. `C:\Users\<your-username>\AppData\Local\napview\data`.

**Q: The visualizer tab is empty or only shows a text message.**  
A: This usually means the data stream has not started or there is no incoming data. Confirm the data source and check the status panel for red warnings. Otherwise check the logs.

**Q: My BrainVision EEG amp does not connect.**  
A: Verify the RDA plugin is enabled and the IP/port are correct.

**Q: Custom LSL stream not found.**  
A: Ensure the stream is running, the stream name matches exactly, and the stream type is EEG.

## How to Cite NAPVIEW

If you use NAPVIEW in your research, please cite the NAPVIEW repository and the underlying models.

### 1. Citing NAPVIEW

```text
Zerr, P. (2025). napview: real-time sleep scoring and analysis visualizer. GitHub. https://github.com/paulzerr/napview
```

### 2. Citing U-Sleep

```text
Perslev, M., et al. (2021). U-Sleep: resilient high-frequency sleep staging. NPJ Digital Medicine.
```

## License

This project is released under the BSD-3 Clause License.

## Contact

For questions, bug reports, or feedback, please contact Paul Zerr at [paul.zerr@donders.ru.nl](mailto:paul.zerr@donders.ru.nl).
