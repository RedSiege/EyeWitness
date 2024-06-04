using System;
using System.IO;
using System.Net;
using System.Threading;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Threading.Tasks;
using System.Linq;
using CommandLine;
using CommandLine.Text;
using System.IO.Compression;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace EyeWitness
{
    class Program
    {
        public static string witnessDir = "";
        public static string catCode = "";
        public static string sigCode = "";
        public static string reportHtml = "";
        private const string CatUrl = "https://raw.githubusercontent.com/RedSiege/EyeWitness/master/Python/categories.txt";
        private const string SigUrl = "https://raw.githubusercontent.com/RedSiege/EyeWitness/master/Python/signatures.txt";
        public static Dictionary<string, string> categoryDict = new Dictionary<string, string>();
        public static Dictionary<string, string> signatureDict = new Dictionary<string, string>();
        public static Dictionary<string, object[]> categoryRankDict = new Dictionary<string, object[]>();
        private static readonly Semaphore Pool = new Semaphore(2,2);
        //private static SemaphoreSlim _pool = new SemaphoreSlim(2);
        private static readonly SemaphoreSlim Sourcepool = new SemaphoreSlim(10);

        public class Options
        {
            public static Options Instance { get; set; }

            // Command line options
            [Option('b', "bookmarks", Group = "Input Source", HelpText = "Searches for bookmark files for IE/Chrome, parses them, and adds them to the list of screenshot URLs")]
            public bool Favorites { get; set; }

            [Option('f', "file", Group = "Input Source", HelpText = "Specify a new-line separated file of URLs", Default = null)]
            public string File { get; set; }

            [Option('i', "cidr", Group = "Input Source", HelpText = "Specify an IP CIDR", Default = null)]
            public string IpAddresses { get; set; }

            [Option('o', "output", Required = false, HelpText = "Specify an output directory (one will be created if non-existent)", Default = null)]
            public string Output { get; set; }

            [Option('d', "delay", Required = false, HelpText = "Specify a delay to use before cancelling a single URL request", Default = 30)]
            public int Delay { get; set; }

            [Option('c', "compress", Required = false, HelpText = "Compress output directory", Default = false)]
            public bool Compress { get; set; }

            [Option("http", Required = false, HelpText = "Prepend http:// to all URLs", Default = false)]
            public bool http { get; set; }

            [Option( "https", Required = false, HelpText = "Prepend https:// to all URLs", Default = false)]
            public bool https { get; set; }
        }

        static void DisplayHelp<T>(ParserResult<T> result)
        {
            var helpText = HelpText.AutoBuild(result, h =>
            {
                h.AdditionalNewLineAfterOption = false;
                h.Heading = "EyeWitness C# Version 1.1"; //change header
                h.Copyright = ""; //change copyright text
                return HelpText.DefaultParsingErrorsHandler(result, h);
            }, e => e);
            Console.WriteLine(helpText);
            System.Environment.Exit(1);
        }

        // The main program will handle determining where the output is saved to, it's not the requirement of the object
        // the object will look up the location where everything should be saved and write to there accordingly
        private static void DirMaker(string output)
        {
            string witnessPath = null;

            if (output == null)
                witnessPath = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            else
            {
                witnessPath = Path.GetFullPath(output);

                if (File.Exists(witnessPath))
                {
                    Console.WriteLine("Output path already exists, using default location");
                    witnessPath = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                }

                if (!Directory.Exists(witnessPath))
                {
                    try
                    {
                        Directory.CreateDirectory(witnessPath);
                    }
                    catch 
                    {
                        witnessPath = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                    }
                }
            }
            
            witnessDir = witnessPath + "\\EyeWitness_" + DateTime.Now.ToString("yyyy-MM-dd_HHmmss");
            Directory.CreateDirectory(witnessDir + "\\src");
            Directory.CreateDirectory(witnessDir + "\\images");
            Directory.CreateDirectory(witnessDir + "\\headers");
        }

        private static void DictMaker()
        {
            // Capture category and signature codes
            // Grab here so we only have to do it once and iterate through URLs in Main
            // Set TLS v1.2
            ServicePointManager.Expect100Continue = true;
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            WebClient witnessClient = new WebClient();

            try
            {
                catCode = witnessClient.DownloadString(CatUrl);
                sigCode = witnessClient.DownloadString(SigUrl);
            }

            catch(Exception ex)
            {
                Console.WriteLine("[*]ERROR: Could not obtain categories and signatures from Github!");
                Console.WriteLine("[*]ERROR: Try again, or see if Github is blocked?");
                Console.WriteLine(ex.Message);
                System.Environment.Exit(1);
            }

            //Create dictionary of categories
            categoryRankDict.Add("highval", new object[] { "High Value Targets", 0 });
            categoryRankDict.Add("virtualization", new object[] { "Virtualization", 0 });
            categoryRankDict.Add("kvm", new object[] { "Remote Console/KVM", 0 });
            categoryRankDict.Add("comms", new object[] { "Communications", 0 });
            categoryRankDict.Add("devops", new object[] { "Development Operations", 0 });
            categoryRankDict.Add("secops", new object[] { "Security Operations", 0 });
            categoryRankDict.Add("appops", new object[] { "Application Operations", 0 });
            categoryRankDict.Add("dataops", new object[] { "Data Operations", 0 });
            categoryRankDict.Add("dirlist", new object[] { "Directory Listings", 0 });
            categoryRankDict.Add("cms", new object[] { "Content Management System (CMS)", 0 });
            categoryRankDict.Add("idrac", new object[] { "IDRAC/ILo/Management Interfaces", 0 });
            categoryRankDict.Add("nas", new object[] { "Network Attached Storage (NAS)", 0 });
            categoryRankDict.Add("netdev", new object[] { "Network Devices", 0 });
            categoryRankDict.Add("voip", new object[] { "Voice/Video over IP (VoIP)", 0 });
            categoryRankDict.Add("None", new object[] { "Uncategorized", 0 });
            categoryRankDict.Add("uncat", new object[] { "Uncategorized", 0 });
            categoryRankDict.Add("crap", new object[] { "Splash Pages", 0 });
            categoryRankDict.Add("printer", new object[] { "Printers", 0 });
            categoryRankDict.Add("camera", new object[] { "Cameras", 0 });
            categoryRankDict.Add("infrastructure", new object[] { "Infrastructure", 0 });
            categoryRankDict.Add("successfulLogin", new object[] { "Successful Logins", 0 });
            categoryRankDict.Add("identifiedLogin", new object[] { "Identified Logins", 0 });
            categoryRankDict.Add("redirector", new object[] { "Redirecting Pages", 0 });
            categoryRankDict.Add("construction", new object[] { "Under Construction", 0 });
            categoryRankDict.Add("empty", new object[] { "No Significant Content", 0 });
            categoryRankDict.Add("unauth", new object[] { "401/403 Unauthorized", 0 });
            categoryRankDict.Add("notfound", new object[] { "404 Not Found", 0 });
            categoryRankDict.Add("badhost", new object[] { "Invalid Hostname", 0 });
            categoryRankDict.Add("inerror", new object[] { "Internal Error", 0 });
            categoryRankDict.Add("badreq", new object[] { "Bad Request", 0 });
            categoryRankDict.Add("badgw", new object[] { "Bad Gateway", 0 });
            categoryRankDict.Add("serviceunavailable", new object[] { "Service Unavailable", 0 });


            // Add files to category dictionary
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
        }

        private static async Task ScreenshotSender(WitnessedServer obj, int timeDelay)
        {
            try
            {
                //Keep it syncronous for this slow version
                //Allow the thread to exit somewhat cleanly before exiting the semaphore
                Pool.WaitOne();
                Console.WriteLine("Grabbing screenshot for: " + obj.remoteSystem);

                WebsiteSnapshot websiteSnapshot = new WebsiteSnapshot(obj.remoteSystem);

                try
                {
                    using (Bitmap bitMap = websiteSnapshot.GenerateWebSiteImage(timeDelay))
                    {
                        bitMap?.Save(obj.imgPath);
                    }
                }
                catch (AccessViolationException e)
                {
                    Console.WriteLine(e);
                }
            }

            catch (OperationCanceledException e)
            {
                Console.WriteLine($"[-] Thread aborted while grabbing screenshot for: {obj.remoteSystem} - {e.Message}");
            }

            catch (SemaphoreFullException)
            {
                //return;
            }

            finally
            {
                Pool?.Release();
            }
        }

        private static async Task SourceSender(WitnessedServer obj)
        {
            try
            {
                await Sourcepool.WaitAsync();
                //Cancel after 10s
                //This cancellation time isn't as important as the screenshot one so we can hard code it
                CancellationTokenSource cts = new CancellationTokenSource(15000);
                Console.WriteLine("Grabbing source of: " + obj.remoteSystem);
                await obj.SourcerAsync(cts.Token);
                obj.CheckCreds(categoryDict, signatureDict);
            }

            catch (OperationCanceledException e)
            {
                Console.WriteLine($"[-] Thread aborted while grabbing source for: {obj.remoteSystem} - {e.Message}");
            }

            catch (SemaphoreFullException)
            {
                //return;
            }

            finally
            {
                Sourcepool?.Release();
            }
        }

        public static void CategoryCounter(WitnessedServer[] urlArray, Dictionary<string, string> catDict)
        {
            //Count how many URLs are in each category
            foreach (WitnessedServer urlObject in urlArray)
            {
                if (categoryRankDict.ContainsKey(urlObject.systemCategory))
                    categoryRankDict[urlObject.systemCategory][1] = (int)categoryRankDict[urlObject.systemCategory][1] + 1;
            }
        }

        public static void Writer(WitnessedServer[] urlArray, string[] allUrlArray)
        {

            int urlCounter = 0;
            int pages = 0;

            Console.WriteLine("\n[*] Writing the reports so you can view as screenshots are taken\n");
            Journalist cronkite = new Journalist();

            // If it's the first page, do something different
            reportHtml = cronkite.InitialReporter(pages, categoryRankDict, allUrlArray.GetLength(0));

            // Iterate through all objects in the array and build the report; taking into account categories
            foreach (KeyValuePair<string, object[]> entry in categoryRankDict)
            {
                int categoryCounter = 0;

                foreach (WitnessedServer witnessedObject in urlArray)
                {
                    try
                    {
                        if (witnessedObject.systemCategory == entry.Key)
                        {
                            // If this is the first instance of the category, create the HTML table
                            if (categoryCounter == 0)
                            {
                                reportHtml += cronkite.CategorizeInitial((string)entry.Value.ElementAt(0), witnessedObject);
                                categoryCounter++;
                            }
                            reportHtml += cronkite.Reporter(witnessedObject);
                            urlCounter++;

                            if (urlCounter == 25)
                            {
                                urlCounter = 0;
                                pages++;
                                reportHtml += "</table>"; //close out the category table
                                cronkite.FinalReporter(reportHtml, pages, allUrlArray.GetLength(0), witnessDir);
                                reportHtml = "";
                                reportHtml = cronkite.InitialReporter(pages, categoryRankDict, allUrlArray.GetLength(0));
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
                cronkite.FinalReporter(reportHtml, pages, allUrlArray.GetLength(0), witnessDir);
            }
        }

        public static List<string> FavoritesParser()
        {
            //Check for favorites files and if they exist parse and add them to the URL array
            List<string> faveUrls = new List<string>();
            List<string> faves = new List<string>();
            string[] ieFaves = Directory.GetFiles(Environment.GetFolderPath(Environment.SpecialFolder.Favorites), "*.*", SearchOption.AllDirectories);
            string chromePath = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData) + "\\Google\\Chrome\\User Data\\Default\\Bookmarks";

            try
            {
                faves.AddRange(ieFaves);
            }

            catch
            {
                Console.WriteLine("[-] Error adding IE favorites, moving on");
            }

            if (faves.Count > 0)
            {
                foreach (var file in faves)
                {
                    using (StreamReader rdr = new StreamReader(file))
                    {
                        string line;
                        while ((line = rdr.ReadLine()) != null)
                        {
                            if (line.StartsWith("URL=", StringComparison.InvariantCultureIgnoreCase))
                            {
                                if (line.Length > 4)
                                {
                                    string url = line.Substring(4);
                                    faveUrls.Add(url);
                                }
                                else
                                    break;
                            }
                        }
                    }
                }
            }

            if (File.Exists(chromePath))
            {
                // Parse Chrome's Json bookmarks file
                string input = File.ReadAllText(chromePath);
                using (StringReader reader = new StringReader(input))
                using (JsonReader jsonReader = new JsonTextReader(reader))
                {
                    JsonSerializer serializer = new JsonSerializer();
                    JToken o = (JToken)serializer.Deserialize(jsonReader);
                    if (o != null)
                    {
                        JToken allChildrens = o["roots"]?["bookmark_bar"]?["children"];

                        try
                        {
                            if (allChildrens != null)
                                foreach (JToken folder in allChildrens)
                                {
                                    // This loop represents items in the bookmark bar
                                    // Have to check for null values first before adding to list
                                    if (folder["url"] != null)
                                        faveUrls.Add(folder["url"].ToString());
                                    if (folder["children"] != null)
                                    {
                                        // This loop represents items in a folder within the bookmark par
                                        foreach (JToken item in folder["children"])
                                        {
                                            if (item["url"] != null)
                                                faveUrls.Add(item["url"].ToString());
                                            if (item["children"] != null)
                                            {
                                                // This loop represents a nested folder within a folder on the bookmarks bar
                                                foreach (JToken subItem in item["children"])
                                                {
                                                    if (subItem["url"] != null)
                                                        faveUrls.Add(subItem["url"].ToString());
                                                }
                                            }
                                        }
                                    }
                                }
                        }
                        catch
                        {
                            Console.WriteLine("[-] Error parsing Google Chrome's bookmarks, moving on");
                        }
                    }
                }
            }

            return faveUrls;
        }

        static void Main(string[] args)
        {
            Console.WriteLine("[+] Firing up EyeWitness...\n");
            string[] allUrls = null;
            List<string> faveUrls = null;
            int delay = 30000;
            Stopwatch watch = new Stopwatch();
            watch.Start();

            //Parse arguments passed
            Parser parser = new Parser(with =>
            {
                with.CaseInsensitiveEnumValues = true;
                with.CaseSensitive = false;
                with.HelpWriter = null;
            });

            ParserResult<Options> parserResult = parser.ParseArguments<Options>(args);
            parserResult.WithParsed(o =>
                {
                    if (o.Delay != 30)
                    {
                        Console.WriteLine("[+] Using a custom timeout of " + o.Delay + " seconds per URL thread");
                        delay = o.Delay * 1000;
                    }

                    else
                        Console.WriteLine("[+] Using the default timeout of 30 seconds per URL thread");

                    if (o.Compress)
                        Console.WriteLine("[+] Compressing files afterwards\n");

                    if(o.Favorites)
                    {
                        // Parse faves
                        Console.WriteLine("[+] Searching and parsing favorites for IE/Chrome...Skipping FireFox for now");
                        faveUrls = FavoritesParser();
                    }

                    if(o.Favorites && o.File == null)
                    {
                        Console.WriteLine("[+] No input file, only using parsed favorites (if any)");
                        try
                        {
                            if (faveUrls != null) allUrls = faveUrls.ToArray();
                        }

                        catch(NullReferenceException)
                        {
                            Console.WriteLine("[-] No favorites or bookmarks found, please try specifying a URL file instead");
                            System.Environment.Exit(1);
                        }
                    }
                    
                    if(o.File != null)
                    {
                        try
                        {
                            if(o.Favorites)
                            {
                                Console.WriteLine("[+] Combining parsed favorites and input file and using that array...");
                                //Combine favorites array and input URLs
                                string[] allUrlsTemp = File.ReadAllLines(o.File);
                                if (faveUrls != null)
                                {
                                    string[] faveUrlsArray = faveUrls.Distinct().ToArray();
                                    allUrls = allUrlsTemp.Concat(faveUrlsArray).Distinct().ToArray();
                                }
                            }

                            else
                            {
                                Console.WriteLine("[+] Using input text file");
                                allUrls = File.ReadAllLines(o.File).Distinct().ToArray();
                            }
                        }
                        catch (FileNotFoundException)
                        {
                            Console.WriteLine("[-] ERROR: The file containing the URLS to scan does not exist!");
                            Console.WriteLine("[-] ERROR: Please make sure you've provided the correct filepath and try again.");
                            System.Environment.Exit(1);
                        }
                    }

                    if (o.IpAddresses != null)
                    {
                        Console.WriteLine("[+] Using IP addresses");

                        try
                        {
                            if (!IPNetwork.TryParse(o.IpAddresses, out var parsed))
                            {
                                Console.WriteLine("[-] ERROR: Failed to parse IP Addresses");
                                return;
                            }

                            var ipAddress = parsed.ListIPAddress().Distinct().ToList();
                            var strings = new List<string>();
                            ipAddress.ForEach(i => strings.Add(i.ToString()));
                            allUrls = strings.ToArray();
                        }
                        catch (Exception e)
                        {
                            Console.WriteLine($"[-] ERROR: {e.Message}");
                            return;
                        }
                    }

                    Options.Instance = o;
                })
                .WithNotParsed(errs => DisplayHelp(parserResult));

            DirMaker(Options.Instance.Output);
            DictMaker();
            Options options = Options.Instance;
            Console.WriteLine("\n");
            // Check for favorites flag and if so add the URLs to the list

            // build an array containing all the web server objects
            WitnessedServer[] serverArray = new WitnessedServer[allUrls.Length];

            //WitnessedServer.SetFeatureBrowserEmulation(); // enable HTML5

            List<Task> sourceTaskList = new List<Task>();
            List<Task> screenshotTaskList = new List<Task>();

            int arrayPosition = 0;

            foreach (var url in allUrls)
            {
                if(!(Uri.TryCreate(url, UriKind.Absolute, out Uri uriResult) && (uriResult.Scheme == Uri.UriSchemeHttp || uriResult.Scheme == Uri.UriSchemeHttps)))
                {
                    if (options.http)
                        Uri.TryCreate($"http://{url}", UriKind.Absolute, out uriResult);

                    else if (options.https)
                        Uri.TryCreate($"https://{url}", UriKind.Absolute, out uriResult);
                    else
                        Uri.TryCreate($"http://{url}", UriKind.Absolute, out uriResult);
                }

                WitnessedServer singleSite = new WitnessedServer(uriResult.AbsoluteUri);
                serverArray[arrayPosition] = singleSite;
                arrayPosition++;

                sourceTaskList.Add(Task.Run(async () =>
                {
                    try
                    {
                        await SourceSender(singleSite);
                    }

                    finally
                    {
                        Sourcepool.Release();
                    }
                }));
            }
            Task.WaitAll(sourceTaskList.ToArray());

            CategoryCounter(serverArray, categoryDict); //Get a list of how many of each category there are
            Writer(serverArray, allUrls); //Write the reportz

            foreach (WitnessedServer entry in serverArray)
            {
                // Grab screenshots separately
                try
                {
                    screenshotTaskList.Add(ScreenshotSender(entry, delay));
                }
                catch
                {
                    Console.WriteLine("Error starting runwithouttimeout on url: " + entry.remoteSystem);
                }
            }

            Thread.Sleep(1000);
            Task.WaitAll(screenshotTaskList.ToArray());

            Thread.Sleep(1000);
            watch.Stop();
            Console.WriteLine("Execution time: " + watch.ElapsedMilliseconds/1000 + " Seconds");
            
            if (options.Compress)
            {
                Console.WriteLine("Compressing output directory...");
                try
                {
                    string zipFileName = witnessDir + ".zip";
                    ZipFile.CreateFromDirectory(witnessDir, zipFileName, CompressionLevel.Optimal, false);
                    Directory.Delete(witnessDir, true);
                }

                catch (Exception ex)
                {
                    Console.WriteLine("[-] Error zipping file");
                    Console.WriteLine(ex);
                }
            }

            Console.WriteLine("Finished! Exiting shortly...");
            //Thread.Sleep(5000);
        }
    }
}
