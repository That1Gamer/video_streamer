# Remote video streamer with interactive frontend
LAN remote camera streamer using a frontend website and Python backend

The initial aim of this project was to create a motion-detecting camera, which could be accessed remotely. 
The system uses Flask to generate the website, and various other python modules to process, record, and track motion. 
Most notably, the OpenCV library was heavily utilised. 

To run this code:
- Make sure the requirements.txt file is installed
- Run the python file on the system with the camera

There were a few improvements which could be made in future revisions:
- Option to automatically take images when motion is detected.
- Use object recognition to determine what is the moving object.
- The recording is inconsistent in terms of real time against recorded time.
- The motion log could update in real time.
- Introduce a feature to select and download a particular recording, rather than the most recent.
- Add connectivity from outside the local network.
- Support for multiple cameras.
