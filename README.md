# FlowController
<img src="https://imgur.com/PPXVbj0.jpg" width="200" height="200">

Python program with GUI for controlling up to 4 Mass Flow Controller heads via a Brooks 0254 (and probably the single head version, Brooks 0251)

Created as part of Sensor Technology course at AGH UST, summer 2020/2021. Later continued as part of my engineering thesis at AGH UST.

## Features
- Up to 4 indepentend tabs controlling individual MFCs connected to device,
- Implementation of most important functions, like Valve Override and Process Configuration,
- Customizable sampling interval and sample buffer size,
- Support for gathering data from up to 2 serial devices per controller,
- Saving gathered data to CSV files,
- (Untested) Control of AR6X2 heating devices, with gradient and readout support
- PyQt graph showing the readouts from device, enabling many functions of this library to be used, 
- Dosing function, which allows the user to specify setpoints at specific points in time,
- Simultaneous starting of dosing processes and saving to CSVs for accurate measurements,
- Support for Sensirion SHT85 and STC31 sensors connected through SEK-SensorBridge,
- Clean, responsive user interface

## Images and videos
![](https://imgur.com/H9ce9ma.jpg)
![](https://imgur.com/wgDWdvY.jpg)

## How to get started 
Download the source code from [here](https://github.com/Soberat/FlowController/archive/refs/heads/main.zip) and extract the contents of the archive.
While in a terminal in the main folder, install the requirements using:
> python -m pip install -r requirements.txt

Then, launch the application using:

> python ./main.py

Choose the VISA response your Brooks 0250 series device is available on, and choose the controllers you want to control:

![](https://imgur.com/HabmBeW.jpg)

And you're ready to control your Brooks 0250 series device!
