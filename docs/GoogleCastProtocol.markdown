GoogleCast Protocol
===================

# Introduction
The GoogleCast protocol is used to send Web Apps to Chromecast devices.  These web apps are written in HTML/JS/CSS and are capable of doing anything you do in a Web Browser.  

While Google has released APIs for iOS, Android, and Chrome, it has not openly released documentation on the protocol which Chromecast uses.  In this document, I will document my attempt to reverse engineer the protocol.  

## Disclaimer
The information below has not been confirmed.  The sections below are based on a what i have found when searching the web.  Some of the info has been confirmed by looking at source code, some has been confirmed through experimentation, and some is simply an educated guess.  Please do not quote me on any of this.

# Overviews 

## Device Services Overview
First, we will analyze what services are currently being run on each device

* Receiver Device (Chromecast)
    * Android Operating System
        * DIAL Server  
            * **DIAL Service Discovery** - This is used to discovery the Chromecast device.
            * **DIAL REST Service** -  This is used to launch Web Apps on the Chromecast device.
        * Chrome Browser 
            * This is a regular Chrome browser.  Once the Web App is loaded, it is ran in this browser. 

* Sender Device
    * DIAL Client
        * This is used to disover Chromecast devices and Launch apps on the Chromecast devices
    * UDP Socket Interface
        * This is used to interface with the Web App's WebSockets.  Play, Pause, and Seek commands are sent via WebSockets


## Launching A Web App Overview
This section will cover all of the steps required to launch a WebApp on A Chromecast Device.

1. Chromecast boots
    * DIAL Server is Running and waiting to receive a Web App
    * Chrome Browser is running and displaying the "Ready to Cast" screen
2. Sender Searches for Chromecast devices using DIAL Service Discovery
    * Sender sends an M-SEARCH request.   
3. Chomecast responds to search request using DIAL Service Discovery 
    * The device responds to inform the Sender of its IP address and Friendly name (ie "Family Room Chromcast")
3. Sender Attempts to Launch a Web App on the Chromecast using the DIAL REST protocol
    * The App-ID is sent to the Chomecast Device
4. Chromecast fetches the Web App URL from Google's Servers
    * The App-ID is sent to Google's server and Google's server responds with the Web App's URL
    * The use of Google Servers is what gives them control over the apps that people and use 
5. Chromecast Loads the Web App URL using the Chromecast Web Browser
    * Loads the HTML, CSS, and Javscript
6. Sender and Chromecast create a WebSocket connection.
    * This connection is used to send playback commands to the Chromecast

# Protocol Details

## Chromecast Discovery
The DIAL discovery is used to discovery new Chromecast device on the network 

* M-Search Request
    * This is sent over UDP on the multicast address 239.255.255.250.
    * The destination port of this Multicast is 1900.  However, the source port will be selected randomly by the OS.
* M-Search Response
    * Chromecast responds with a LOCATION header that contains a URL to the Chromecast Info XML file.  This URL gives us the IP, the port, and the info path of the device.
    * This is sent with a UDP unicast back to the Requestor's IP address.  The port it uses will be the same as the M-Search Request's "source" port
* Device Description Request/Response
    * Once you have the Location header, you can request the devices Info XML file and gather more details.
    * The XML body contains the devices Friendly name.  This allows the user to identify each device easily.
    * The HTTP Headers contain the Application URL path.  This is used to launch and manage apps.

## Launch and Manage Running Apps
The DIAL REST is used to manage Web applications on the Chromecast.

* Launch Request
    * Sender asks for the Chromecast to Launch the provided App
    * The App-ID is sent using an HTTP POST request.
    * The 'Origin' header needs to be set in order to request an app.  
        * Chromecast will barf (404) if this is not correct
        * Currently, i am using the GoogleCast Chome Extension's Origin.  I is the same as the Extension's URL (chrome-extension://boadgeojelhgndaghljhdicfkmllpafd)
        * I am guessing this is just to track usage data (ie Chrome vs iOS vs Android apps).  Hopefully this ID doesnt change often (not the end of the world, but it would be annoying
    * The Body of the POST request contains app launching arguments.  These arguments are URL encoded (like a GET url).  
        * The pairingCode argument must be there.  I am guessing this is used to identify sessions.  For now, i am just generating a UUID each time and seems to be cool with it.  
* Fetch Web App
    * Chromecast sends App-ID to google's servers.  Google responds with the Web App's URL
    * The App's URL is loaded into the Chromecast Browser and displpayed on the screen
* Launch Response
    * Chromecast responds to the HTTP request with a 201 message.
    * The body of the response is empty, but the headers contain some info about the app.  More specifically, it contains a "Location" header that can be used to kill the app later.  

You can also kill web apps.  To do this, you just have to send a "DELETE" request to the Apps instance URL.  

## WebSocket Commands
Once the Web App is loaded on the Chromecast, WebSockets are used to send playback commands to the Chromecast device.  Some examples of playback commands are Play, Pause, and Seek.

The exact commands are not known at this time, but we can probably figure them out by looking at the GoogleCast Chrome App source code.  The Chrome App is 100% javascript so you can read the source. However, the variables are renamed to make it difficult to read.  Its kind of annoying, but it'll help with reverse engineering.
  
Google provides an API for these playback commands. However, it is technically possible to create your own API for controlling yoru Web App.  Since we control the Reciever and Sender applications, we could use any protocol we want within WebSockets. 

# Whitelisting
For this project to work, you will need to whitelist your device.  When you whitelist your device, you notify Google that it is OK to use your device for development purposes.

## Why?
In order to launch an app, you need an App-ID.  In order to get an App-ID, you need to register your app and device with Google.  When you send the App-ID to the Chromecast, the Chomecast SW asks a Google server for the App URL.  If you want Google's server to return a URL, you will need to send your device serial number and App URL to Google.  The App-ID is linked to the serial number so you will need your own App-ID.  You cant use mine.

## How?
Google has a form on the GoogleCast developer site.  When filling out the form, i just told the truth.  I told them i was making an app to send items from my NAS to my Chromecast.  For the URLs, I put a local URL (http://192.168.0.200/chromecast) in the box.  48 hours later, i recieved an App-ID.  

It looks like Google is not very critcal when handing out App-IDs so there is no need to lie.  I also like that they let me use a Local URL.  That will make it much simpler. (No need to register a Domain name or modify my local DNS server)

**NOTE:** You will need to setup the Chromecast to send its serial number to Google's servers.  In the Chomecast Setup app, check the "Send this Chomecast's serial number when checking for updates"

## Sharing App-IDs
I am not sure if its safe to share App-IDs.  I will keep mine private for now, but i may share it down the road if i learn it is OK.

## Testing Whitelist Status
After a device is whitelisted, you will be able to look at the debug info.  Open a browser and go to http://[Chromecast IP Address]:9222.  if it works, you're device is now whitelisted.  

If this doesnt work, verify your Chromecast is setup correctly (sending its serial number to Google) and then reboot the Chromecast (pull the USB cable)



