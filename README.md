EyeWitness
======

EyeWitness is designed to take screenshots of websites, provide some server header info, and identify default credentials if possible.

Inspiration came from Tim Tomes's PeepingTom Script.  I just wanted to change some things, and then it became a thought exercise to write it myself.

EyeWitness is designed to run on Kali Linux.  It will auto detect the file you give it with the -f flag as either being a text file with URLs on each new line, nmap xml output, or nessus xml output.  The -t (timeout) flag is completely optional, and lets you provice the max time to wait when trying to render and screenshot a web page.  The --open flag, which is optional, will open the URL in a new tab within iceweasel.


E-Mail: EyeWitness [@] christophertruncer [dot] com

Setup:

1. Navigate into the setup directory
2. Run the setup.sh script

Usage:

./EyeWitness.py -f filename -t optionaltimeout --open (Optional)

Examples:

./EyeWitness -f urls.txt

./EyeWitness -f urls.xml -t 8 --open

Thanks:
Thanks to Jason Hill (@jasonhillva) for helping to get the xml parsing working.  And thanks to the group of guys I work with giving me their thoughts on new features I could add in, ways to optimize the code, and more.

Call to Action:
I'd love for EyeWitness to identify more default credentials of various web applications.  As you find a device which utilizes default credentials, please e-mail me the source code of the index page and the default creds so I can add it in to EyeWitness!