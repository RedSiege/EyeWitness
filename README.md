EyeWitness
======

EyeWitness is designed to take screenshots of websites provide some server header info, and identify default credentials if known.

EyeWitness is designed to run on Kali Linux. It will auto detect the file you give it with the -f flag as either being a text file with URLs on each new line, nmap xml output, or nessus xml output. The --timeout flag is completely optional, and lets you provide the max time to wait when trying to render and screenshot a web page.

A complete usage guide which documents EyeWitness features and its typical use cases is available here - https://www.christophertruncer.com/eyewitness-usage-guide/

## Windows
FortyNorth Security has created a Windows client (thanks to the massive help of Matt Grandy (@Matt_Grandy_) with the stability fixes). All you need to do is build it locally (or check the releases), and then provide a path to a file containing the URLs you want scanned! EyeWitness will generate the report within your "AppData\Roaming" directory.

### Setup:
1. Navigate into the CS directory 
2. Load EyeWitness.sln into Visual Studio
3. Go to Build at the top and then Build Solution if no modifications are wanted

### Usage:
```bash
EyeWitness.exe --help
EyeWitness.exe -f C:\Path\to\urls.txt
EyeWitness.exe -f C:\Path\to\urls.txt -d [timeout in seconds] -c
```

## Linux

###### Supported Linux Distros:
* Kali Linux
* Debian 7+ (at least stable, looking into testing) (Thanks to @themightyshiv)

**E-Mail:** EyeWitness [@] christophertruncer [dot] com

### Setup:
1. Navigate into the setup directory
2. Run the setup.sh script

### Usage:
```bash
./EyeWitness.py -f filename --timeout optionaltimeout
```

### Examples:
```bash
./EyeWitness -f urls.txt --web

./EyeWitness -x urls.xml --timeout 8 

./EyeWitness.py -f urls.txt --web --proxy-ip 127.0.0.1 --proxy-port 8080 --proxy-type socks5 --timeout 120
```

### Proxy Usage
The best guide for proxying EyeWitness through a socks proxy was made by @raikia and is available here - https://github.com/FortyNorthSecurity/EyeWitness/issues/458

### Docker
Now you can execute EyeWitness in a docker container and prevent you from install unnecessary dependencies in your host machine.

**Note:** execute *docker run* with the folder path in the host which hold your results (**/path/to/results**)  
**Note2:** in case you want to scan urls from a file, make sure you put it in the volume folder (if you put *urls.txt* in */path/to/results*, then the argument should be *-f /tmp/EyeWitness/urls.txt*)

##### Usage
```bash
docker build --build-arg user=$USER --tag eyewitness --file ./Python/Dockerfile .
docker run \
    --rm \
    -it \
    -e DISPLAY=$DISPLAY \                   # optional flag in order to use vnc protocol
    -v /tmp/.X11-unix:/tmp/.X11-unix \      # optional flag in order to use vnc protocol
    -v /path/to/results:/tmp/EyeWitness \
    eyewitness \
    EyeWitness_flags_and_input
```

##### Example #1 - headless capturing
```bash
docker run \
    --rm \
    -it \
    -v ~/EyeWitness:/tmp/EyeWitness \
    eyewitness \
    --web \
    --single http://www.google.com
```

###### Call to Action:
I'd love for EyeWitness to identify more default credentials of various web applications.  
As you find a device which utilizes default credentials, please e-mail me the source code of the index page and the default creds so I can add it in to EyeWitness!
