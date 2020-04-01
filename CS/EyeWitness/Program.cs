using System;
using System.IO;
using System.Net;
using System.Threading;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Linq;

namespace EyeWitness
{
    class Program
    {
        public static string witnessDir = "";
        public static string catCode = "";
        public static string sigCode = "";
        public static string reportHtml = "";
        static string catURL = "https://raw.githubusercontent.com/FortyNorthSecurity/EyeWitness/master/Python/categories.txt";
        static string sigURL = "https://raw.githubusercontent.com/FortyNorthSecurity/EyeWitness/master/Python/signatures.txt";
        public static Dictionary<string, string> categoryDict = new Dictionary<string, string>();
        public static Dictionary<string, string> signatureDict = new Dictionary<string, string>();
        public static Dictionary<string, object[]> categoryRankDict = new Dictionary<string, object[]>();
        private static Semaphore _pool = new Semaphore(1,1);
        //private static SemaphoreSlim _pool = new SemaphoreSlim(2);
        private static SemaphoreSlim _Sourcepool = new SemaphoreSlim(10);


        // The main program will handle determining where the output is saved to, it's not the requirement of the object
        // the object will look up the location where everything should be saved and write to there accordingly
        static void DirMaker()
        {
            string witnessPath = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            witnessDir = witnessPath + "\\EyeWitness_" + DateTime.Now.ToString("MM.dd.yy.HH.mm.ss");
            Directory.CreateDirectory(witnessDir + "\\src");
            Directory.CreateDirectory(witnessDir + "\\images");
            Directory.CreateDirectory(witnessDir + "\\headers");
            return;
        }

        static void DictMaker()
        {
            // Capture category and signature codes
            // Grab here so we only have to do it once and iterate through URLs in Main
            WebClient witnessClient = new WebClient();
            try
            {
                catCode = witnessClient.DownloadString(catURL);
                sigCode = witnessClient.DownloadString(sigURL);
            }
            catch
            {
                Console.WriteLine("[*]ERROR: Could not obtain categories and signatures from Github!");
                Console.WriteLine("[*]ERROR: Try again, or see if Github is blocked?");
                System.Environment.Exit(1);
            }

            //Create dictionary of categories
            categoryRankDict.Add("highval", new object[] { "High Value Targets", 0 });
            categoryRankDict.Add("dirlist", new object[] { "Directory Listings", 0 });
            categoryRankDict.Add("None", new object[] { "Uncategorized", 0 });
            categoryRankDict.Add("uncat", new object[] { "Uncategorized", 0 });
            categoryRankDict.Add("cms", new object[] { "Content Management System (CMS)", 0 });
            categoryRankDict.Add("idrac", new object[] { "IDRAC/ILo/Management Interfaces", 0 });
            categoryRankDict.Add("nas", new object[] { "Network Attached Storage (NAS)", 0 });
            categoryRankDict.Add("construction", new object[] { "Under Construction", 0 });
            categoryRankDict.Add("netdev", new object[] { "Network Devices", 0 });
            categoryRankDict.Add("voip", new object[] { "Voice/Video over IP (VoIP)", 0 });
            categoryRankDict.Add("unauth", new object[] { "401/403 Unauthorized", 0 });
            categoryRankDict.Add("notfound", new object[] { "404 Not Found", 0 });
            categoryRankDict.Add("crap", new object[] { "Splash Pages", 0 });
            categoryRankDict.Add("printer", new object[] { "Printers", 0 });
            categoryRankDict.Add("successfulLogin", new object[] { "Successful Logins", 0 });
            categoryRankDict.Add("identifiedLogin", new object[] { "Identified Logins", 0 });
            categoryRankDict.Add("infrastructure", new object[] { "Infrastructure", 0 });
            categoryRankDict.Add("redirector", new object[] { "Redirecting Pages", 0 });
            categoryRankDict.Add("badhost", new object[] { "Invalid Hostname", 0 });
            categoryRankDict.Add("inerror", new object[] { "Internal Error", 0 });
            categoryRankDict.Add("badreq", new object[] { "Bad Request", 0 });
            categoryRankDict.Add("serviceunavailable", new object[] { "Service Unavailable", 0 });


            // Add files to cagegory dictionary
            foreach (string line in catCode.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None))
            {
                try
                {
                    string[] splitLine = line.Split('|');
                    categoryDict.Add(splitLine[0], splitLine[1]);
                }
                catch
                {
                    // line doesn't work, but continue anyway
                }
            }

            // Add files to signature dictionary
            foreach (string line in sigCode.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.None))
            {
                try
                {
                    string[] splitLine = line.Split('|');
                    signatureDict.Add(splitLine[0], splitLine[1]);
                }
                catch
                {
                    // line doesn't work, but continue anyway
                }
            }
            return;
        }

        private static async Task ScreenshotSender(WitnessedServer obj, int timeDelay)
        {
            //Cancel after 30s
            var cts = new CancellationTokenSource(30000);
            cts.CancelAfter(30000);
            try
            {
                //Keep it syncronous for this slow version
                _pool.WaitOne(40000);

                Console.WriteLine("Grabbing screenshot for: " + obj.remoteSystem);
                //obj.RunWithTimeout(TimeSpan.FromMilliseconds(timeDelay));
                var task = await obj.RunWithTimeoutCancellation(cts.Token);



                _pool.Release();
            }
            catch (OperationCanceledException)
            {
                Console.WriteLine("[-] Thread aborted while grabbing screenshot for: " + obj.remoteSystem);
            }
            catch (SemaphoreFullException)
            {
                //return;
            }
        }

        private static async Task SourceSender(WitnessedServer obj)
        {
            //Cancel after 10s
            var cts = new CancellationTokenSource(10000);
            cts.CancelAfter(10000);

            try
            {
                await _Sourcepool.WaitAsync(10000);
                Console.WriteLine("Grabbing source of: " + obj.remoteSystem);
                await obj.SourcerAsync(cts.Token);
                obj.CheckCreds(categoryDict, signatureDict);

                _Sourcepool.Release();
            }
            catch (OperationCanceledException)
            {
                Console.WriteLine("[-] Thread aborted while grabbing source for: " + obj.remoteSystem);
            }
            catch (SemaphoreFullException)
            {
                //return;
            }
        }

        public static void CategoryCounter(WitnessedServer[] urlArray, Dictionary<string, string> catDict)
        {
            //Count how many URLs are in each category
            foreach (var urlObject in urlArray)
            {
                if (categoryRankDict.ContainsKey(urlObject.systemCategory))
                {
                    categoryRankDict[urlObject.systemCategory][1] = (int)categoryRankDict[urlObject.systemCategory][1] + 1;
                }               
            }
        }

        public static void Writer(WitnessedServer[] urlArray, string[] allUrlArray)
        {

            int urlCounter = 0;
            int pages = 0;

            Console.WriteLine("[*] Writing the reports so you can view as screenshots are taken");
            Journalist Cronkite = new Journalist();

            // If it's the first page, do something different
            reportHtml = Cronkite.InitialReporter(pages, categoryRankDict, allUrlArray.GetLength(0));

            // Iterate throught all objects in the array and build the report; taking into account categories
            foreach (KeyValuePair<string, object[]> entry in categoryRankDict)
            {
                int categoryCounter = 0;

                foreach (var witnessedObject in urlArray)
                {
                    try
                    {
                        if (witnessedObject.systemCategory == entry.Key)
                        {
                            // If this is the first instance of the category, create the HTML table
                            if (categoryCounter == 0)
                            {
                                reportHtml += Cronkite.CategorizeInitial((string)entry.Value.ElementAt(0), witnessedObject);
                                categoryCounter++;
                            }
                            reportHtml += Cronkite.Reporter(witnessedObject);
                            urlCounter++;

                            if (urlCounter == 25)
                            {
                                urlCounter = 0;
                                pages++;
                                reportHtml += "</table>"; //close out the category table
                                Cronkite.FinalReporter(reportHtml, pages, allUrlArray.GetLength(0), witnessDir);
                                reportHtml = "";
                                reportHtml = Cronkite.InitialReporter(pages, categoryRankDict, allUrlArray.GetLength(0));
                                categoryCounter = 0;
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("Error is - " + ex);
                    }
                }
            }

            if (allUrlArray.GetLength(0) % 25 == 0)
            {
                //pass since the report was already written and finalized
            }
            else
            {
                pages++; //need to increase before final write (takes into account 0 pages from above block
                reportHtml += "</table>"; //close out the category table
                Cronkite.FinalReporter(reportHtml, pages, allUrlArray.GetLength(0), witnessDir);
            }

        }

        static void Main(string[] args)
        {
            Console.WriteLine("[+] Firing up EyeWitness...");
            DirMaker();
            DictMaker();
            string[] allUrls = null;
            int delay = 30000;
            var watch = new System.Diagnostics.Stopwatch();
            watch.Start();


            // Read in URLs
            //Account for 2 arguments - the first is the file of URLs the second is the timeout
            if (args.Length == 2)
            {
                try
                {
                    allUrls = System.IO.File.ReadAllLines(args[0]);
                    delay = Int32.Parse(args[1]);
                }
                catch (FileNotFoundException)
                {
                    Console.WriteLine("\n[*] ERROR: The file containing the URLS to scan does not exist!");
                    Console.WriteLine("[*] ERROR: Please make sure you've provided the correct filepath and try again.");
                    return;
                }
                catch
                {
                    Console.WriteLine("Invalid int for timeout, using the default of 30 seconds");
                    delay = 30000; //Set the delay to default to 10s
                }
            }
            else if (args.Length == 1)
            {
                try
                {
                    allUrls = System.IO.File.ReadAllLines(args[0]);
                    Console.WriteLine("Using the default timeout of 10 seconds");
                }
                catch (Exception e)
                {
                    Console.WriteLine("Error when running. Error thrown: \n" + e);
                }
            }
            else
            {
                Console.WriteLine("\n[*] ERROR: Please specify a URL file to use\n");
                Console.WriteLine("\n\n[++] Usage: EyeWitness.exe c:\\Path\\To\\URLs.txt [Timeout] (ex. 10000 = 10 seconds)");
                Console.WriteLine("[++] EyeWitness.exe c:\\users\\test\\urls.txt");
                Console.WriteLine("[++] EyeWitness.exe c:\\users\\test\\urls.txt 20000");
                System.Environment.Exit(1);
            }

            // build an array containing all the web server objects
            WitnessedServer[] serverArray = new WitnessedServer[allUrls.Length];

            // Build an array containing the objects so we can easily loop over them
            Console.WriteLine("[+] Using a delay of: " + delay + " (in milliseconds)");
            //WitnessedServer.SetFeatureBrowserEmulation(); // enable HTML5

            List<Task> SourceTaskList = new List<Task>();
            List<Task> ScreenshotTaskList = new List<Task>();

            int arrayPosition = 0;
            foreach (var url in allUrls)
            {
                WitnessedServer singleSite = new WitnessedServer(url);
                serverArray[arrayPosition] = singleSite;
                arrayPosition++;

                SourceTaskList.Add(Task.Run(async () =>
                {
                    try
                    {
                        await SourceSender(singleSite);
                    }
                    finally
                    {
                        _Sourcepool.Release();
                    }
                }));
            }
            Task.WaitAll(SourceTaskList.ToArray());

            CategoryCounter(serverArray, categoryDict); //Get a list of how many of each category there are

            Writer(serverArray, allUrls); //Write the reportz

            foreach (var entry in serverArray)
            {
                // Grab screenshots separately
                try
                {
                    ScreenshotTaskList.Add(ScreenshotSender(entry, delay));
                }
                catch
                {
                    Console.WriteLine("Error starting runwithouttimeout on url: " + entry.remoteSystem);
                }
            }
            Thread.Sleep(1000);
            Task.WaitAll(ScreenshotTaskList.ToArray());

            Thread.Sleep(1000);
            watch.Stop();
            Console.WriteLine("Execution time: " + watch.ElapsedMilliseconds/1000 + " Seconds");
            Console.WriteLine("Finished! Exiting shortly...");
            Thread.Sleep(5000);
            return;
        }
    }
}